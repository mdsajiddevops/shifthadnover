#!/usr/bin/env python3
"""
Migration Script: Add User Team Memberships Support
Purpose: Migrate from single team per user to multiple teams support
Date: 2025-11-26
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models.models import User, Team, Account, UserTeamMembership
from sqlalchemy import text
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the migration to add user team memberships support"""
    
    with app.app_context():
        try:
            logger.info("🚀 Starting migration: Add User Team Memberships Support")
            
            # Step 1: Create the new table
            logger.info("📝 Creating user_team_memberships table...")
            
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS `user_team_memberships` (
              `id` int NOT NULL AUTO_INCREMENT,
              `user_id` int NOT NULL,
              `team_id` int NOT NULL,
              `account_id` int NOT NULL,
              `is_primary` tinyint(1) NOT NULL DEFAULT '0',
              `role` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'member',
              `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
              `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              `added_by_id` int DEFAULT NULL,
              `is_active` tinyint(1) NOT NULL DEFAULT '1',
              PRIMARY KEY (`id`),
              UNIQUE KEY `unique_user_team_per_account` (`user_id`, `team_id`, `account_id`),
              KEY `user_id` (`user_id`),
              KEY `team_id` (`team_id`),
              KEY `account_id` (`account_id`),
              KEY `added_by_id` (`added_by_id`),
              KEY `idx_primary_team` (`user_id`, `is_primary`),
              KEY `idx_user_teams_active` (`user_id`, `is_active`),
              KEY `idx_team_members_active` (`team_id`, `is_active`),
              KEY `idx_account_members` (`account_id`, `is_active`),
              CONSTRAINT `user_team_memberships_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
              CONSTRAINT `user_team_memberships_ibfk_2` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`) ON DELETE CASCADE,
              CONSTRAINT `user_team_memberships_ibfk_3` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`) ON DELETE CASCADE,
              CONSTRAINT `user_team_memberships_ibfk_4` FOREIGN KEY (`added_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            
            db.session.execute(text(create_table_sql))
            db.session.commit()
            logger.info("✅ user_team_memberships table created successfully")
            
            # Step 2: Migrate existing user-team relationships
            logger.info("📦 Migrating existing user-team relationships...")
            
            users_with_teams = User.query.filter(
                User.team_id.isnot(None),
                User.account_id.isnot(None)
            ).all()
            
            migrated_count = 0
            for user in users_with_teams:
                try:
                    # Check if membership already exists
                    existing = UserTeamMembership.query.filter_by(
                        user_id=user.id,
                        team_id=user.team_id,
                        account_id=user.account_id
                    ).first()
                    
                    if not existing:
                        # Create new membership record
                        membership = UserTeamMembership(
                            user_id=user.id,
                            team_id=user.team_id,
                            account_id=user.account_id,
                            is_primary=True,  # Existing assignments become primary
                            role='member',
                            is_active=True,
                            created_at=user.created_at or datetime.now()
                        )
                        
                        db.session.add(membership)
                        migrated_count += 1
                        
                        if migrated_count % 50 == 0:
                            db.session.commit()
                            logger.info(f"   Migrated {migrated_count} users so far...")
                    
                except Exception as e:
                    logger.error(f"❌ Error migrating user {user.id} ({user.username}): {e}")
                    db.session.rollback()
            
            db.session.commit()
            logger.info(f"✅ Migrated {migrated_count} existing user-team relationships")
            
            # Step 3: Create view for easy querying
            logger.info("🔍 Creating user_teams_view...")
            
            create_view_sql = """
            CREATE OR REPLACE VIEW `user_teams_view` AS
            SELECT 
                u.id as user_id,
                u.username,
                u.email,
                u.first_name,
                u.last_name,
                utm.team_id,
                t.name as team_name,
                utm.account_id,
                a.name as account_name,
                utm.is_primary,
                utm.role as team_role,
                utm.is_active as membership_active,
                utm.created_at as membership_created
            FROM user u
            JOIN user_team_memberships utm ON u.id = utm.user_id
            JOIN team t ON utm.team_id = t.id
            JOIN account a ON utm.account_id = a.id
            WHERE utm.is_active = 1 AND u.is_active = 1 AND t.is_active = 1
            """
            
            db.session.execute(text(create_view_sql))
            db.session.commit()
            logger.info("✅ user_teams_view created successfully")
            
            # Step 4: Verify migration
            logger.info("🔍 Verifying migration results...")
            
            total_memberships = UserTeamMembership.query.count()
            primary_memberships = UserTeamMembership.query.filter_by(is_primary=True).count()
            active_memberships = UserTeamMembership.query.filter_by(is_active=True).count()
            
            logger.info(f"📊 Migration Results:")
            logger.info(f"   Total memberships: {total_memberships}")
            logger.info(f"   Primary memberships: {primary_memberships}")
            logger.info(f"   Active memberships: {active_memberships}")
            logger.info(f"   Users with teams: {len(set(m.user_id for m in UserTeamMembership.query.all()))}")
            
            # Check for data integrity issues
            users_with_multiple_primary = db.session.execute(text("""
                SELECT user_id, COUNT(*) as primary_count
                FROM user_team_memberships 
                WHERE is_primary = 1 
                GROUP BY user_id 
                HAVING COUNT(*) > 1
            """)).fetchall()
            
            if users_with_multiple_primary:
                logger.warning(f"⚠️  Found {len(users_with_multiple_primary)} users with multiple primary teams")
                for row in users_with_multiple_primary:
                    logger.warning(f"   User ID {row[0]} has {row[1]} primary teams")
            else:
                logger.info("✅ Data integrity check passed - no users with multiple primary teams")
            
            # Step 5: Show sample data
            logger.info("📄 Sample migrated data:")
            sample_memberships = UserTeamMembership.query.limit(5).all()
            for membership in sample_memberships:
                user = User.query.get(membership.user_id)
                team = Team.query.get(membership.team_id)
                account = Account.query.get(membership.account_id)
                logger.info(f"   {user.username} -> {team.name} ({account.name}) [Primary: {membership.is_primary}]")
            
            logger.info("🎉 Migration completed successfully!")
            logger.info("")
            logger.info("📋 Next steps:")
            logger.info("1. Update application code to use UserTeamMembership model")
            logger.info("2. Update user management interface")
            logger.info("3. Test the multi-team functionality")
            logger.info("4. Consider keeping user.team_id for backward compatibility (optional)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            db.session.rollback()
            return False

def rollback_migration():
    """Rollback the migration (for development/testing purposes)"""
    
    with app.app_context():
        try:
            logger.info("🔄 Rolling back migration: Add User Team Memberships Support")
            
            # Drop the view
            logger.info("🗑️  Dropping user_teams_view...")
            db.session.execute(text("DROP VIEW IF EXISTS user_teams_view"))
            
            # Drop the table
            logger.info("🗑️  Dropping user_team_memberships table...")
            db.session.execute(text("DROP TABLE IF EXISTS user_team_memberships"))
            
            db.session.commit()
            logger.info("✅ Migration rollback completed successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            db.session.rollback()
            return False

def main():
    """Main function to run migration or rollback"""
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "rollback":
            return rollback_migration()
        elif sys.argv[1] == "status":
            # Check if migration has been applied
            with app.app_context():
                try:
                    result = db.session.execute(text("SHOW TABLES LIKE 'user_team_memberships'")).fetchone()
                    if result:
                        count = UserTeamMembership.query.count()
                        logger.info(f"✅ Migration has been applied. {count} team memberships found.")
                    else:
                        logger.info("❌ Migration has not been applied yet.")
                except Exception as e:
                    logger.error(f"Error checking migration status: {e}")
            return
    
    # Default: run migration
    success = run_migration()
    
    if success:
        logger.info("\n🚀 Migration completed successfully!")
        logger.info("You can now use the multi-team functionality in your application.")
    else:
        logger.error("\n❌ Migration failed! Please check the errors above and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()