-- ============================================
-- Migration 002: Add UserPreferences table
-- ============================================
-- Stores user preferences as extensible JSON
-- Supports: voice settings, and future preferences
-- ============================================

-- Create UserPreferences table
CREATE TABLE UserPreferences (
    UserId NVARCHAR(255) PRIMARY KEY,  -- Entra ID object ID (same as ShoppingLists)
    Preferences NVARCHAR(MAX) NOT NULL DEFAULT '{}',  -- JSON blob for extensibility
    CreatedAt DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    UpdatedAt DATETIME2 NOT NULL DEFAULT GETUTCDATE()
);

-- Add index for faster lookups (though PK already covers this)
CREATE INDEX IX_UserPreferences_UserId ON UserPreferences(UserId);

-- ============================================
-- Example JSON structure for Preferences column:
-- {
--   "voice": {
--     "name": "en-US-AriaNeural",
--     "rate": "+20%"
--   }
-- }
-- ============================================
