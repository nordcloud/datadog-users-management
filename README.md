# datadog-users-management
Script to modify Datadog users based on file containing APP and API keys. 
This file should be generated using https://github.com/nordcloud/mc-monitoring-configuration/blob/master/scripts/generate_keys/generate_keys.py


It performs the following actions (on all organizations which details are in source file:
* Disables Datadog users who left the company
* Disables Datadog users with 'Pending' status
* Changes access level for internal users to 'Standard' if their previous role was 'Admin' and they're not members of MCT
* Changes access level for all external users to 'Read-only'

In the future this script might be integrated with TCA.