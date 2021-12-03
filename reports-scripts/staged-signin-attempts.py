# Install dependencies 
# pip install okta
import asyncio
import datetime
from okta.client import Client as OktaClient

# Update these values
org_url = '<<Org Base URL>>'
api_token = '<<API Token>>'
group_id = '<<Group ID>>'

okta_client = OktaClient({
    'orgUrl': org_url,
    'token': api_token
}) 

async def main():    
    # Get staged users in assigned group
    group_users = await get_group_users(group_id)
    staged_users = filter_users_by_status(group_users, 'STAGED')
    staged_userids = list(map(lambda u: u.profile.login, staged_users))

    # Get logs of user sign in attemtps
    end_time = datetime.datetime.utcnow()
    start_time = end_time - datetime.timedelta(days=15)
    unidentified_signins = await get_unknown_user_logins(start_time.isoformat(), end_time.isoformat())
    unidentified_userids = set()
    for log in unidentified_signins:
        unidentified_userids.add(log.actor.alternate_id)

    # Join these two get staged users who have attempted to sign in 
    staged_logins =[]
    for uuid in unidentified_userids:
        # Check Complete match
        if (uuid in staged_userids):
            staged_logins.append(uuid)
        # Check Partial matches - might add multiple
        elif any(f'{uuid}@' in suid for suid in staged_userids):
            matches = [muid for muid in staged_userids if f'{uuid}@' in muid]
            for match in matches:
                staged_logins.append(match)

    # Printed for sample
    print('staged_logins')
    for u in staged_logins:
        print(u)

async def get_group_users(groupId, query_parameters = {'limit': '100'}):
    group_users = []
    users, resp, err = await okta_client.list_group_users(groupId, query_parameters)
    while True:
        group_users.extend(users)
        if resp.has_next():
            users, err = await resp.next()
        else:
            break
    return group_users

def filter_users_by_status(users, status):
    return list(filter(lambda u: u.status == status, users))

async def get_unknown_user_logins(since, until):
    query_params = {
        'filter': 'outcome.reason eq "VERIFICATION_ERROR" AND eventType eq "user.session.start"',
        'since': since,
        'until': until
    }
    filtered_logs =[]
    logs, resp, err = await okta_client.get_logs(query_params)
    iter = 1
    while True:
        iter += 1
        filtered_logs.extend(logs)
        if resp.has_next():
            logs, err = await resp.next()
        else:
            break
    return filtered_logs

loop = asyncio.get_event_loop()
loop.run_until_complete(main())