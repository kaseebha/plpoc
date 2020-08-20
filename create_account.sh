#/bin/bash

#Get product-id, provisioning-artifact-id
#aws servicecatalog search-products --filters FullTextSearch='AWS Control Tower Account Factory'
#aws servicecatalog describe-product --id prod-XXXXXXXXXXXXXXX


PROVISIONED_PRODUCT_NAME="dev-acct-"$(date | md5 | head -c5)
PROVISION_TOKEN=$(date | md5)
PRODUCT_ID="prod-n2mfbfheqlkzm"
PROVISIONING_ARTIFACT_ID="pa-pyewfptayx4im"
PARAM_FILE="file://params.json"

echo "Creating Account Factory account: "$PROVISIONED_PRODUCT_NAME

aws servicecatalog provision-product --product-id $PRODUCT_ID --provisioning-artifact-id $PROVISIONING_ARTIFACT_ID --provision-token $PROVISION_TOKEN --provisioned-product-name $PROVISIONED_PRODUCT_NAME --provisioning-parameters file://params.json

