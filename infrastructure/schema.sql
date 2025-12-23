-- ============================================
-- Alexa Cooking Assistant - Database Schema
-- SQL Server / Azure SQL Database
-- ============================================

-- ============================================
-- TABLES
-- ============================================

-- Recipes: Core recipe metadata
CREATE TABLE Recipes (
    RecipeId INT IDENTITY(1,1) PRIMARY KEY,
    Name NVARCHAR(200) NOT NULL,
    Description NVARCHAR(MAX) NULL,
    SourceType NVARCHAR(100) NULL,
    SourceURL NVARCHAR(500) NULL,
    Cuisine NVARCHAR(100) NULL,
    Category NVARCHAR(100) NULL,
    PrepTime INT NULL,
    CookTime INT NULL,
    Servings INT NULL,
    CreatedDate DATETIME NOT NULL DEFAULT(GETDATE())
);

-- Ingredients: Normalized ingredient names (deduplicated)
CREATE TABLE Ingredients (
    IngredientId INT IDENTITY(1,1) PRIMARY KEY,
    Name NVARCHAR(100) NOT NULL UNIQUE
);

-- UnitsOfMeasure: Normalized units (deduplicated)
CREATE TABLE UnitsOfMeasure (
    UnitId INT IDENTITY(1,1) PRIMARY KEY,
    UnitName NVARCHAR(50) NOT NULL UNIQUE
);

-- RecipeIngredients: Links recipes to ingredients with quantities
CREATE TABLE RecipeIngredients (
    RecipeIngredientId INT IDENTITY(1,1) PRIMARY KEY,
    RecipeId INT NOT NULL,
    IngredientId INT NOT NULL,
    UnitId INT NULL,
    Quantity NVARCHAR(50) NULL,
    OrderIndex INT NOT NULL,
    CONSTRAINT FK_RecipeIngredients_Recipes
        FOREIGN KEY (RecipeId) REFERENCES Recipes(RecipeId) ON DELETE CASCADE,
    CONSTRAINT FK_RecipeIngredients_Ingredients
        FOREIGN KEY (IngredientId) REFERENCES Ingredients(IngredientId),
    CONSTRAINT FK_RecipeIngredients_UnitsOfMeasure
        FOREIGN KEY (UnitId) REFERENCES UnitsOfMeasure(UnitId)
);

-- Steps: Recipe preparation steps in order
CREATE TABLE Steps (
    StepId INT IDENTITY(1,1) PRIMARY KEY,
    RecipeId INT NOT NULL,
    Description NVARCHAR(MAX) NOT NULL,
    OrderIndex INT NOT NULL,
    CONSTRAINT FK_Steps_Recipes
        FOREIGN KEY (RecipeId) REFERENCES Recipes(RecipeId) ON DELETE CASCADE
);

-- ============================================
-- SHOPPING LIST TABLES
-- ============================================

-- ShoppingLists: Shopping list for meal planning
-- UserId stores the Entra ID object ID (GUID) of the list owner
CREATE TABLE ShoppingLists (
    ShoppingListId INT IDENTITY(1,1) PRIMARY KEY,
    UserId NVARCHAR(255) NOT NULL,  -- Entra ID object ID
    Name NVARCHAR(200) NULL,
    CreatedDate DATETIME NOT NULL DEFAULT(GETDATE()),
    Status NVARCHAR(50) NOT NULL DEFAULT 'active'  -- active, completed, archived
);

-- ShoppingListRecipes: Links shopping lists to recipes with planning details
CREATE TABLE ShoppingListRecipes (
    ShoppingListRecipeId INT IDENTITY(1,1) PRIMARY KEY,
    ShoppingListId INT NOT NULL,
    RecipeId INT NOT NULL,
    Servings INT NULL,
    PlannedDate DATE NULL,
    MealType NVARCHAR(50) NULL,  -- breakfast, lunch, dinner, snack
    CONSTRAINT FK_ShoppingListRecipes_ShoppingLists
        FOREIGN KEY (ShoppingListId) REFERENCES ShoppingLists(ShoppingListId) ON DELETE CASCADE,
    CONSTRAINT FK_ShoppingListRecipes_Recipes
        FOREIGN KEY (RecipeId) REFERENCES Recipes(RecipeId)
);

-- ShoppingListItems: Aggregated ingredients in a shopping list
CREATE TABLE ShoppingListItems (
    ShoppingListItemId INT IDENTITY(1,1) PRIMARY KEY,
    ShoppingListId INT NOT NULL,
    IngredientId INT NOT NULL,
    AggregatedQuantity NVARCHAR(100) NULL,
    Category NVARCHAR(50) NULL,  -- produce, meat, dairy, pantry
    IsChecked BIT NOT NULL DEFAULT 0,
    SortOrder INT NULL,
    CONSTRAINT FK_ShoppingListItems_ShoppingLists
        FOREIGN KEY (ShoppingListId) REFERENCES ShoppingLists(ShoppingListId) ON DELETE CASCADE,
    CONSTRAINT FK_ShoppingListItems_Ingredients
        FOREIGN KEY (IngredientId) REFERENCES Ingredients(IngredientId)
);

-- ShoppingListLinks: Shareable links for shopping lists
CREATE TABLE ShoppingListLinks (
    LinkId INT IDENTITY(1,1) PRIMARY KEY,
    ShoppingListId INT NOT NULL,
    LinkCode NVARCHAR(20) NOT NULL UNIQUE,
    CreatedDate DATETIME NOT NULL DEFAULT(GETDATE()),
    ExpiresDate DATETIME NULL,
    CONSTRAINT FK_ShoppingListLinks_ShoppingLists
        FOREIGN KEY (ShoppingListId) REFERENCES ShoppingLists(ShoppingListId) ON DELETE CASCADE
);

-- GroceryPrices: Cached price data from grocery store APIs
CREATE TABLE GroceryPrices (
    GroceryPriceId INT IDENTITY(1,1) PRIMARY KEY,
    IngredientId INT NOT NULL,
    StoreName NVARCHAR(100) NOT NULL,
    ProductName NVARCHAR(300) NULL,
    ProductId NVARCHAR(100) NULL,
    Price DECIMAL(10, 2) NULL,
    Unit NVARCHAR(50) NULL,
    LastUpdated DATETIME NOT NULL DEFAULT(GETDATE()),
    CONSTRAINT FK_GroceryPrices_Ingredients
        FOREIGN KEY (IngredientId) REFERENCES Ingredients(IngredientId)
);

-- ============================================
-- INDEXES
-- ============================================

-- Optimize "get step N of recipe X" queries
CREATE INDEX IX_Steps_RecipeId_OrderIndex
ON Steps(RecipeId, OrderIndex);

-- Optimize "get ingredient N of recipe X" queries
CREATE INDEX IX_RecipeIngredients_RecipeId_OrderIndex
ON RecipeIngredients(RecipeId, OrderIndex);

-- Optimize recipe search by name
CREATE INDEX IX_Recipes_Name
ON Recipes(Name);

-- Optimize recipe filtering by category/cuisine
CREATE INDEX IX_Recipes_Category
ON Recipes(Category);

CREATE INDEX IX_Recipes_Cuisine
ON Recipes(Cuisine);

-- Optimize shopping list queries by status
CREATE INDEX IX_ShoppingLists_Status
ON ShoppingLists(Status);

-- Optimize shopping list queries by user
CREATE INDEX IX_ShoppingLists_UserId
ON ShoppingLists(UserId);

-- Optimize shopping list item lookups
CREATE INDEX IX_ShoppingListItems_ShoppingListId
ON ShoppingListItems(ShoppingListId);

-- Optimize shareable link lookups
CREATE INDEX IX_ShoppingListLinks_LinkCode
ON ShoppingListLinks(LinkCode);

-- ============================================
-- USER-DEFINED TABLE TYPES
-- ============================================

-- For bulk ingredient insertion
CREATE TYPE IngredientInputTableType AS TABLE (
    Name NVARCHAR(100) NOT NULL,
    Quantity NVARCHAR(50) NOT NULL,
    Unit NVARCHAR(50) NULL,
    OrderIndex INT NOT NULL
);

-- For bulk step insertion
CREATE TYPE StepInputTableType AS TABLE (
    Description NVARCHAR(MAX) NOT NULL,
    OrderIndex INT NOT NULL
);

-- ============================================
-- STORED PROCEDURES
-- ============================================

GO
CREATE OR ALTER PROCEDURE InsertRecipeWithIngredientsAndSteps
(
    @Name NVARCHAR(200),
    @Description NVARCHAR(MAX),
    @SourceType NVARCHAR(100),
    @SourceURL NVARCHAR(500),
    @Cuisine NVARCHAR(100),
    @Category NVARCHAR(100),
    @PrepTime INT,
    @CookTime INT,
    @Servings INT,
    @Ingredients IngredientInputTableType READONLY,
    @Steps StepInputTableType READONLY
)
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRANSACTION;

    BEGIN TRY
        -- Insert recipe metadata
        INSERT INTO Recipes (Name, Description, SourceType, SourceURL, Cuisine, Category, PrepTime, CookTime, Servings, CreatedDate)
        VALUES (@Name, @Description, @SourceType, @SourceURL, @Cuisine, @Category, @PrepTime, @CookTime, @Servings, GETDATE());

        DECLARE @RecipeId INT = SCOPE_IDENTITY();

        -- Insert unique ingredients (skip existing)
        ;WITH DistinctIngredients AS (
            SELECT DISTINCT Name FROM @Ingredients
        )
        INSERT INTO Ingredients (Name)
        SELECT DI.Name
        FROM DistinctIngredients DI
        LEFT JOIN Ingredients I ON I.Name = DI.Name
        WHERE I.Name IS NULL;

        -- Insert unique units of measure (skip existing)
        ;WITH DistinctUnits AS (
            SELECT DISTINCT Unit FROM @Ingredients WHERE Unit IS NOT NULL AND Unit <> ''
        )
        INSERT INTO UnitsOfMeasure (UnitName)
        SELECT DU.Unit
        FROM DistinctUnits DU
        LEFT JOIN UnitsOfMeasure U ON U.UnitName = DU.Unit
        WHERE U.UnitName IS NULL;

        -- Link ingredients to recipe
        INSERT INTO RecipeIngredients (RecipeId, IngredientId, UnitId, Quantity, OrderIndex)
        SELECT
            @RecipeId,
            I.IngredientId,
            U.UnitId,
            T.Quantity,
            T.OrderIndex
        FROM @Ingredients T
        JOIN Ingredients I ON I.Name = T.Name
        LEFT JOIN UnitsOfMeasure U ON T.Unit = U.UnitName;

        -- Insert steps
        INSERT INTO Steps (RecipeId, Description, OrderIndex)
        SELECT @RecipeId, S.Description, S.OrderIndex
        FROM @Steps S;

        -- Return the new recipe ID
        SELECT @RecipeId AS RecipeId;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END
GO

-- ============================================
-- STORED PROCEDURE: Delete Recipe
-- ============================================

CREATE OR ALTER PROCEDURE DeleteRecipe
(
    @RecipeId INT
)
AS
BEGIN
    SET NOCOUNT ON;

    -- CASCADE handles RecipeIngredients and Steps automatically
    DELETE FROM Recipes WHERE RecipeId = @RecipeId;

    -- Return rows affected (0 = not found, 1 = deleted)
    SELECT @@ROWCOUNT AS RowsDeleted;
END
GO

-- ============================================
-- STORED PROCEDURE: Get Recipe with Details
-- ============================================

CREATE OR ALTER PROCEDURE GetRecipeWithDetails
(
    @RecipeId INT
)
AS
BEGIN
    SET NOCOUNT ON;

    -- Result set 1: Recipe metadata
    SELECT
        RecipeId,
        Name,
        Description,
        SourceType,
        SourceURL,
        Cuisine,
        Category,
        PrepTime,
        CookTime,
        Servings,
        CreatedDate
    FROM Recipes
    WHERE RecipeId = @RecipeId;

    -- Result set 2: Ingredients in order
    SELECT
        ri.RecipeIngredientId,
        ri.OrderIndex,
        i.Name AS IngredientName,
        ri.Quantity,
        u.UnitName
    FROM RecipeIngredients ri
    JOIN Ingredients i ON ri.IngredientId = i.IngredientId
    LEFT JOIN UnitsOfMeasure u ON ri.UnitId = u.UnitId
    WHERE ri.RecipeId = @RecipeId
    ORDER BY ri.OrderIndex;

    -- Result set 3: Steps in order
    SELECT
        StepId,
        OrderIndex,
        Description
    FROM Steps
    WHERE RecipeId = @RecipeId
    ORDER BY OrderIndex;
END
GO

-- ============================================
-- SAMPLE DATA (Optional)
-- ============================================

/*
-- Uncomment to insert sample recipe

DECLARE @Ingredients IngredientInputTableType;
DECLARE @Steps StepInputTableType;

INSERT INTO @Ingredients (Name, Quantity, Unit, OrderIndex)
VALUES
    ('Italian sausage', '1', 'pound', 1),
    ('onion', '1 medium, diced', NULL, 2),
    ('carrots', '2 medium, diced', NULL, 3),
    ('celery ribs', '2, diced', NULL, 4),
    ('garlic', '2', 'cloves', 5),
    ('brown lentils', '1', 'pound', 6),
    ('low-sodium chicken stock', '8', 'cups', 7),
    ('dried thyme', '1', 'teaspoon', 8),
    ('bay leaves', '2', NULL, 9),
    ('salt and pepper', 'to taste', NULL, 10),
    ('extra virgin olive oil', 'for drizzling', NULL, 11),
    ('Pecorino Romano cheese', 'for serving', NULL, 12),
    ('crusty bread', 'for serving', NULL, 13);

INSERT INTO @Steps (Description, OrderIndex)
VALUES
    ('Heat oil in a large pot over medium heat.', 1),
    ('Add sausage and brown well, breaking it into pieces.', 2),
    ('Add onion, carrots, and celery. Cook until softened, about 5 minutes.', 3),
    ('Add garlic and stir for 30 seconds until fragrant.', 4),
    ('Add lentils, chicken stock, thyme, and bay leaves. Bring to a boil, then reduce heat and simmer until lentils are tender, about 45 minutes.', 5),
    ('Remove bay leaves. Season with salt and pepper to taste.', 6),
    ('Serve drizzled with olive oil, topped with Pecorino Romano, alongside crusty bread.', 7);

EXEC InsertRecipeWithIngredientsAndSteps
    @Name = 'Sausage Lentil Soup',
    @Description = 'A hearty Italian sausage and lentil soup perfect for cooler weather.',
    @SourceType = 'Website',
    @SourceURL = 'https://www.sipandfeast.com/sausage-lentil-soup/',
    @Cuisine = 'Italian-American',
    @Category = 'Soup',
    @PrepTime = 15,
    @CookTime = 60,
    @Servings = 8,
    @Ingredients = @Ingredients,
    @Steps = @Steps;
*/
