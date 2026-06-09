#!/bin/bash
# Creates all Firestore composite indexes needed by Kiwi TCMS.
# Run once; Firestore builds each index asynchronously (1-5 min each).
# Re-running is safe — existing indexes are ignored.

set -e
PROJECT="kiwi-tcms-d90e9"
DB="(default)"

create_index() {
    local collection="$1"
    shift
    echo "Creating index on $collection ($*)..."
    gcloud firestore indexes composite create \
        --project="$PROJECT" \
        --database="$DB" \
        --collection-group="$collection" \
        "$@" 2>&1 | grep -v "^$" || true
}

# management_priority: filter(is_active=True) + Meta.ordering=["value"]
create_index management_priority \
    --field-config=field-path=is_active,order=ASCENDING \
    --field-config=field-path=value,order=ASCENDING \
    --field-config=field-path=__name__,order=ASCENDING

# management_priority: filter_objects(is_active=True).order_by("id") from priority_dao
create_index management_priority \
    --field-config=field-path=is_active,order=ASCENDING \
    --field-config=field-path=__name__,order=ASCENDING

# management_version: filter(product_id=X) + Meta.ordering=["value"]
create_index management_version \
    --field-config=field-path=product_id,order=ASCENDING \
    --field-config=field-path=value,order=ASCENDING \
    --field-config=field-path=__name__,order=ASCENDING

# management_version: version_dao order_by("product", "id")
create_index management_version \
    --field-config=field-path=product_id,order=ASCENDING \
    --field-config=field-path=__name__,order=ASCENDING

# testcases_category: filter(product_id=X) + Meta.ordering=["name"]
create_index testcases_category \
    --field-config=field-path=product_id,order=ASCENDING \
    --field-config=field-path=name,order=ASCENDING \
    --field-config=field-path=__name__,order=ASCENDING

# management_component: filter(product_id=X) + Meta.ordering=["name"]
create_index management_component \
    --field-config=field-path=product_id,order=ASCENDING \
    --field-config=field-path=name,order=ASCENDING \
    --field-config=field-path=__name__,order=ASCENDING

# management_build: filter(product_id=X) + Meta.ordering=["name"]
create_index management_build \
    --field-config=field-path=product_id,order=ASCENDING \
    --field-config=field-path=name,order=ASCENDING \
    --field-config=field-path=__name__,order=ASCENDING

# management_build: build_dao order_by("version", "id")
create_index management_build \
    --field-config=field-path=version_id,order=ASCENDING \
    --field-config=field-path=__name__,order=ASCENDING

# management_build: filter(version_id__in=[...]) + Meta.ordering=["name"]
# from bugs/forms.py NewBugForm.populate()
create_index management_build \
    --field-config=field-path=version_id,order=ASCENDING \
    --field-config=field-path=name,order=ASCENDING \
    --field-config=field-path=__name__,order=ASCENDING

# testruns_environment: order_by("name", "description")
create_index testruns_environment \
    --field-config=field-path=name,order=ASCENDING \
    --field-config=field-path=description,order=ASCENDING \
    --field-config=field-path=__name__,order=ASCENDING

# testruns_environmentproperty: order_by("environment", "name", "value")
create_index testruns_environmentproperty \
    --field-config=field-path=environment_id,order=ASCENDING \
    --field-config=field-path=name,order=ASCENDING \
    --field-config=field-path=value,order=ASCENDING \
    --field-config=field-path=__name__,order=ASCENDING

# testruns_testrun: filter(plan_id=X, stop_date__isnull=True).order_by("-id")
# from testplans/views.py GetTestPlanView
create_index testruns_testrun \
    --field-config=field-path=plan_id,order=ASCENDING \
    --field-config=field-path=stop_date,order=ASCENDING \
    --field-config=field-path=__name__,order=DESCENDING

# testruns_testrun: filter(manager=user, stop_date__isnull=True)
# from core/views.py DashboardView
create_index testruns_testrun \
    --field-config=field-path=manager_id,order=ASCENDING \
    --field-config=field-path=stop_date,order=ASCENDING \
    --field-config=field-path=__name__,order=ASCENDING

# testruns_testrun: filter(default_tester=user, stop_date__isnull=True)
# from core/views.py DashboardView
create_index testruns_testrun \
    --field-config=field-path=default_tester_id,order=ASCENDING \
    --field-config=field-path=stop_date,order=ASCENDING \
    --field-config=field-path=__name__,order=ASCENDING

# testplans_testplan: filter(author=user).order_by("-pk")
# from core/views.py DashboardView
create_index testplans_testplan \
    --field-config=field-path=author_id,order=ASCENDING \
    --field-config=field-path=__name__,order=DESCENDING

# testplans_testplan: filter(parent_id=X).order_by("pk")
# from testplans/models.py tree_as_list
create_index testplans_testplan \
    --field-config=field-path=parent_id,order=ASCENDING \
    --field-config=field-path=__name__,order=ASCENDING

echo ""
echo "All index creation requests submitted."
echo "Indexes build asynchronously — check status at:"
echo "https://console.firebase.google.com/project/$PROJECT/firestore/indexes"
