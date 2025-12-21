-- ============================================
-- Shopping List Schema Migration
-- Run after initial schema.sql
-- ============================================

-- ============================================
-- NEW TABLES
-- ============================================

-- Shopping lists (can exist independent of meal plans)
CREATE TABLE ShoppingLists (
    ShoppingListId INT IDENTITY(1,1) PRIMARY KEY,
    Name NVARCHAR(200) NULL,
    CreatedDate DATETIME NOT NULL DEFAULT(GETDATE()),
    Status NVARCHAR(50) NOT NULL DEFAULT 'active'  -- active, completed, archived
);

-- Link shopping lists to recipes (with optional serving multiplier)
CREATE TABLE ShoppingListRecipes (
    ShoppingListRecipeId INT IDENTITY(1,1) PRIMARY KEY,
    ShoppingListId INT NOT NULL,
    RecipeId INT NOT NULL,
    Servings INT NULL,  -- NULL = use recipe default
    PlannedDate DATE NULL,  -- optional: assign to a day
    MealType NVARCHAR(50) NULL,  -- breakfast, lunch, dinner, snack
    CONSTRAINT FK_ShoppingListRecipes_ShoppingLists
        FOREIGN KEY (ShoppingListId) REFERENCES ShoppingLists(ShoppingListId) ON DELETE CASCADE,
    CONSTRAINT FK_ShoppingListRecipes_Recipes
        FOREIGN KEY (RecipeId) REFERENCES Recipes(RecipeId)
);

-- Consolidated shopping list items (aggregated from recipes)
CREATE TABLE ShoppingListItems (
    ShoppingListItemId INT IDENTITY(1,1) PRIMARY KEY,
    ShoppingListId INT NOT NULL,
    IngredientId INT NOT NULL,
    AggregatedQuantity NVARCHAR(100) NULL,  -- "3 medium" or "2 lbs"
    Category NVARCHAR(50) NULL,  -- produce, meat, dairy, pantry, etc.
    IsChecked BIT NOT NULL DEFAULT 0,
    SortOrder INT NULL,
    CONSTRAINT FK_ShoppingListItems_ShoppingLists
        FOREIGN KEY (ShoppingListId) REFERENCES ShoppingLists(ShoppingListId) ON DELETE CASCADE,
    CONSTRAINT FK_ShoppingListItems_Ingredients
        FOREIGN KEY (IngredientId) REFERENCES Ingredients(IngredientId)
);

-- For shareable list links
CREATE TABLE ShoppingListLinks (
    LinkId INT IDENTITY(1,1) PRIMARY KEY,
    ShoppingListId INT NOT NULL,
    LinkCode NVARCHAR(20) NOT NULL UNIQUE,  -- Short code like "x7k2m"
    CreatedDate DATETIME NOT NULL DEFAULT(GETDATE()),
    ExpiresDate DATETIME NULL,
    CONSTRAINT FK_ShoppingListLinks_ShoppingLists
        FOREIGN KEY (ShoppingListId) REFERENCES ShoppingLists(ShoppingListId) ON DELETE CASCADE
);

-- Price snapshots from grocery APIs (for Phase 6)
CREATE TABLE GroceryPrices (
    GroceryPriceId INT IDENTITY(1,1) PRIMARY KEY,
    IngredientId INT NOT NULL,
    StoreName NVARCHAR(100) NOT NULL,  -- Kroger, Walmart, H-E-B, etc.
    ProductName NVARCHAR(300) NULL,  -- Actual product matched
    ProductId NVARCHAR(100) NULL,  -- Store's product ID for cart integration
    Price DECIMAL(10,2) NULL,
    Unit NVARCHAR(50) NULL,  -- per lb, each, per oz
    LastUpdated DATETIME NOT NULL DEFAULT(GETDATE()),
    CONSTRAINT FK_GroceryPrices_Ingredients
        FOREIGN KEY (IngredientId) REFERENCES Ingredients(IngredientId)
);

-- ============================================
-- INDEXES
-- ============================================

-- Optimize shopping list item lookups
CREATE INDEX IX_ShoppingListItems_ShoppingListId
ON ShoppingListItems(ShoppingListId);

-- Optimize shopping list recipe lookups
CREATE INDEX IX_ShoppingListRecipes_ShoppingListId
ON ShoppingListRecipes(ShoppingListId);

-- Optimize link code lookups
CREATE UNIQUE INDEX IX_ShoppingListLinks_LinkCode
ON ShoppingListLinks(LinkCode);

-- Optimize price lookups by ingredient and store
CREATE INDEX IX_GroceryPrices_IngredientId_StoreName
ON GroceryPrices(IngredientId, StoreName);

-- ============================================
-- STORED PROCEDURES
-- ============================================

GO
CREATE OR ALTER PROCEDURE CreateShoppingListFromRecipes
(
    @Name NVARCHAR(200),
    @RecipeIds NVARCHAR(MAX)  -- Comma-separated recipe IDs
)
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRANSACTION;

    BEGIN TRY
        -- Create the shopping list
        INSERT INTO ShoppingLists (Name, CreatedDate, Status)
        VALUES (@Name, GETDATE(), 'active');

        DECLARE @ShoppingListId INT = SCOPE_IDENTITY();

        -- Parse recipe IDs and insert links
        INSERT INTO ShoppingListRecipes (ShoppingListId, RecipeId)
        SELECT @ShoppingListId, value
        FROM STRING_SPLIT(@RecipeIds, ',')
        WHERE RTRIM(LTRIM(value)) <> '';

        -- Return the new shopping list ID
        SELECT @ShoppingListId AS ShoppingListId;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END
GO

CREATE OR ALTER PROCEDURE GetShoppingListWithItems
(
    @ShoppingListId INT
)
AS
BEGIN
    SET NOCOUNT ON;

    -- Result set 1: Shopping list metadata
    SELECT
        sl.ShoppingListId,
        sl.Name,
        sl.CreatedDate,
        sl.Status
    FROM ShoppingLists sl
    WHERE sl.ShoppingListId = @ShoppingListId;

    -- Result set 2: Recipes in this list
    SELECT
        slr.ShoppingListRecipeId,
        slr.RecipeId,
        r.Name AS RecipeName,
        slr.Servings,
        slr.PlannedDate,
        slr.MealType
    FROM ShoppingListRecipes slr
    JOIN Recipes r ON slr.RecipeId = r.RecipeId
    WHERE slr.ShoppingListId = @ShoppingListId;

    -- Result set 3: Aggregated items
    SELECT
        sli.ShoppingListItemId,
        i.Name AS IngredientName,
        sli.AggregatedQuantity,
        sli.Category,
        sli.IsChecked,
        sli.SortOrder
    FROM ShoppingListItems sli
    JOIN Ingredients i ON sli.IngredientId = i.IngredientId
    WHERE sli.ShoppingListId = @ShoppingListId
    ORDER BY sli.Category, sli.SortOrder, i.Name;
END
GO

CREATE OR ALTER PROCEDURE GetShoppingListByLinkCode
(
    @LinkCode NVARCHAR(20)
)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @ShoppingListId INT;

    SELECT @ShoppingListId = ShoppingListId
    FROM ShoppingListLinks
    WHERE LinkCode = @LinkCode
      AND (ExpiresDate IS NULL OR ExpiresDate > GETDATE());

    IF @ShoppingListId IS NOT NULL
        EXEC GetShoppingListWithItems @ShoppingListId;
END
GO

CREATE OR ALTER PROCEDURE ToggleShoppingListItem
(
    @ShoppingListItemId INT
)
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE ShoppingListItems
    SET IsChecked = CASE WHEN IsChecked = 1 THEN 0 ELSE 1 END
    WHERE ShoppingListItemId = @ShoppingListItemId;

    SELECT IsChecked FROM ShoppingListItems WHERE ShoppingListItemId = @ShoppingListItemId;
END
GO
