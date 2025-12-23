-- ============================================
-- Migration: Add UserId to ShoppingLists
-- ============================================
-- This migration adds multi-user support by adding a UserId column
-- to the ShoppingLists table. The UserId stores the Azure Entra ID
-- object ID (GUID) of the list owner.
--
-- IMPORTANT: Before running this migration, you need to decide what
-- to do with existing shopping lists. The options are:
--
-- Option 1: Assign all existing lists to a default/admin user
--           Update the @DefaultUserId variable below
--
-- Option 2: Delete all existing lists (only for dev/test environments)
--           Uncomment the DELETE statement below
--
-- ============================================

-- Set a default user ID for existing lists
-- Replace with your admin user's Entra ID object ID
DECLARE @DefaultUserId NVARCHAR(255) = 'SYSTEM-MIGRATION-USER';

-- ============================================
-- Step 1: Add the UserId column (nullable initially)
-- ============================================
IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'ShoppingLists' AND COLUMN_NAME = 'UserId'
)
BEGIN
    ALTER TABLE ShoppingLists
    ADD UserId NVARCHAR(255) NULL;

    PRINT 'Added UserId column to ShoppingLists';
END
ELSE
BEGIN
    PRINT 'UserId column already exists in ShoppingLists';
END
GO

-- ============================================
-- Step 2: Populate UserId for existing records
-- ============================================

-- Option 1: Assign to default user (recommended for production)
UPDATE ShoppingLists
SET UserId = @DefaultUserId
WHERE UserId IS NULL;

PRINT 'Updated existing shopping lists with default user';

-- Option 2: Delete existing lists (uncomment for dev/test only)
-- DELETE FROM ShoppingLists WHERE UserId IS NULL;
-- PRINT 'Deleted existing shopping lists without user';

GO

-- ============================================
-- Step 3: Make UserId NOT NULL
-- ============================================
IF EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'ShoppingLists'
    AND COLUMN_NAME = 'UserId'
    AND IS_NULLABLE = 'YES'
)
BEGIN
    ALTER TABLE ShoppingLists
    ALTER COLUMN UserId NVARCHAR(255) NOT NULL;

    PRINT 'Made UserId column NOT NULL';
END
GO

-- ============================================
-- Step 4: Add index for efficient user queries
-- ============================================
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_ShoppingLists_UserId'
    AND object_id = OBJECT_ID('ShoppingLists')
)
BEGIN
    CREATE INDEX IX_ShoppingLists_UserId
    ON ShoppingLists(UserId);

    PRINT 'Created index IX_ShoppingLists_UserId';
END
ELSE
BEGIN
    PRINT 'Index IX_ShoppingLists_UserId already exists';
END
GO

-- ============================================
-- Verification
-- ============================================
SELECT
    'ShoppingLists' AS TableName,
    COUNT(*) AS TotalRecords,
    COUNT(DISTINCT UserId) AS UniqueUsers
FROM ShoppingLists;

PRINT 'Migration complete: UserId column added to ShoppingLists';
GO
