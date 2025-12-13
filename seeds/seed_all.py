"""
Global seeder for the o_test schema.

Runs all seeding blocks in the correct sequence:
1) USERS BLOCK (users, profile_settings, user_contacts, user_tags, users_user_tags)
2) WAYS BLOCK (users_projects, projects, ways, way_tags, ways_way_tags, way_collections, way_collections_ways, composite_ways)
4) ACTIVITY BLOCK (day_reports, metrics, plans, plans_job_tags, problems, job_dones, job_dones_job_tags)
5) SOCIAL BLOCK (comments, favorite_users, favorite_users_ways)
6) MENTORING BLOCK (mentor_users_ways, former_mentors_ways, from_user_mentoring_requests, to_user_mentoring_requests)
"""

from seeds.seed_users_block import seed_users_block
from seeds.seed_ways_block import seed_ways_block
from seeds.seed_activity_block import seed_activity_block
from seeds.seed_social_block import seed_social_block
from seeds.seed_mentoring_block import seed_mentoring_block

def main():
    print("\n===GLOBAL SEED START ===\n")

    print(">>> 1/5: USERS")
    seed_users_block()

    print("\n>>> 2/5: WAYS")
    seed_ways_block()

    print("\n>>> 3/5: ACTIVITY")
    seed_activity_block()

    print("\n>>> 4/5: SOCIAL")
    seed_social_block()

    print("\n>>> 5/5: MENTORING")
    seed_mentoring_block()

    print("\n=== GLOBAL SEED DONE ===\n")

if __name__ == "__main__":
    main()
