#!/bin/bash

python - << EOF
import firecloud.api as fapi
print(fapi.whoami)
status_url='https://app.terra.bio/#workspaces/kco-tech/Gut_eQTL/job_history/1576f1bd-4507-4013-aae4-f1c3b2c1baf6'
entries = status_url.split('/')
workspace_namespace, workspace_name, submission_id = [entries[idx] for idx in [-4, -3, -1]]
response = fapi.get_submission(workspace_namespace, workspace_name, submission_id)
print(response.text)
EOF
