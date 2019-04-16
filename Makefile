ROOT_DIR	:= $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
AWS_REGION	:= us-west-2
AWS_PROFILE := 
TENABLE_IO := Y
KMS_POLICY_FILE := 
KMS_KEYID := 

$(info Checking if Tenable.io support is needed...)
ifeq ($(TENABLE_IO), Y)
  TENABLE_ACCESS_KEY = ${TIOA}
  TENABLE_SECRET_KEY = ${TIOS}
  ifeq ($(KMS_POLICY_FILE), )
    ifeq ($(KSM_KEYID), )
      DEFAULT_KMS = Y
	endif
  else
    KMS_DESCRIPTION := "KMS key for vautomator-serverless"
    KMS_KEYID := $(shell aws --profile '$(AWS_PROFILE)' kms create-key --policy \
	file://./'$(KMS_POLICY_FILE)' --description '$(KMS_DESCRIPTION)' --query 'KeyMetadata.KeyId')
  endif
endif

all:
	@echo 'Available make targets:'
	# TODO: Debug, remove later
	@echo $(TENABLE_ACCESS_KEY)
	@echo $(TENABLE_SECRET_KEY)
	@grep '^[^#[:space:]^\.PHONY.*].*:' Makefile

.SILENT: setup
.PHONY: setup
ifdef DEFAULT_KMS
  setup:
	export AWS_SDK_LOAD_CONFIG=true && \
	aws --profile $(AWS_PROFILE) ssm put-parameter --name "TENABLEIO_ACCESS_KEY" \
	--value $(TENABLE_ACCESS_KEY) --type SecureString --overwrite && \
	aws --profile $(AWS_PROFILE) ssm put-parameter --name "TENABLEIO_SECRET_KEY" \
	--value $(TENABLE_SECRET_KEY) --type SecureString --overwrite && \
	npm install serverless-python-requirements --save-dev
else
  ifdef KMS_KEYID
    setup:
	export AWS_SDK_LOAD_CONFIG=true && \
	aws --profile $(AWS_PROFILE) ssm put-parameter --name "TENABLEIO_ACCESS_KEY" \
	--value $(TENABLE_ACCESS_KEY) --type SecureString --key-id $(KMS_KEYID) --overwrite && \
	aws --profile $(AWS_PROFILE) ssm put-parameter --name "TENABLEIO_SECRET_KEY" \
	--value $(TENABLE_SECRET_KEY) --type SecureString --key-id $(KMS_KEYID) --overwrite && \
	npm install serverless-python-requirements --save-dev
  else
    $(info Could not get KEYID!)
  endif
endif
	
.PHONY: validate
validate: export AWS_SDK_LOAD_CONFIG=true
validate:
	sls deploy --noDeploy --region $(AWS_REGION) --aws-profile $(AWS_PROFILE)

.PHONY: deploy
deploy: export AWS_SDK_LOAD_CONFIG=true
deploy:
	sls deploy --region $(AWS_REGION) --aws-profile $(AWS_PROFILE)

.PHONY: test
test:
	python -m pytest tests/

.PHONY: flake8
flake8:
	flake8 ./*py
	flake8 lib/*py
	flake8 scanners/*py
	flake8 examples/*py
	flake8 tests/*py

.PHONY: clean
clean:
	find . -name .pytest_cache -type d -exec rm -rf {}\;
	find . -name __pycache__ -type d -exec rm -rf {}\;