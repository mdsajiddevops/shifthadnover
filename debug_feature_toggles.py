"""
Debug Feature Toggles Script
This script will help diagnose feature toggle issues
"""

from app import app
from models.app_config import AppConfig

def debug_feature_toggles():
    with app.app_context():
        print("=== FEATURE TOGGLE DEBUG ===")
        
        # Check all feature configurations
        all_configs = AppConfig.query.all()
        print(f"Total configurations: {len(all_configs)}")
        
        feature_configs = AppConfig.query.filter(AppConfig.config_key.like('feature_%')).all()
        print(f"Feature configurations: {len(feature_configs)}")
        
        for config in feature_configs:
            print(f"  {config.config_key}: '{config.config_value}' (type: {type(config.config_value)})")
        
        # Test the is_feature_enabled function
        print("\n=== TESTING is_feature_enabled FUNCTION ===")
        
        # Import the function
        from app import is_feature_enabled
        
        # Test the specific features
        servicenow_enabled = is_feature_enabled('feature_servicenow_integration')
        ctask_enabled = is_feature_enabled('feature_ctask_assignment')
        
        print(f"ServiceNow Integration enabled: {servicenow_enabled}")
        print(f"CTask Assignment enabled: {ctask_enabled}")
        
        # Test direct AppConfig calls
        print("\n=== DIRECT AppConfig CALLS ===")
        servicenow_direct = AppConfig.get_config('feature_servicenow_integration', default='true')
        ctask_direct = AppConfig.get_config('feature_ctask_assignment', default='true')
        
        print(f"ServiceNow direct: '{servicenow_direct}' (lower: {servicenow_direct.lower()})")
        print(f"CTask direct: '{ctask_direct}' (lower: {ctask_direct.lower()})")
        
        print(f"ServiceNow comparison: '{servicenow_direct.lower()}' == 'true' = {servicenow_direct.lower() == 'true'}")
        print(f"CTask comparison: '{ctask_direct.lower()}' == 'true' = {ctask_direct.lower() == 'true'}")

if __name__ == '__main__':
    debug_feature_toggles()