#!/bin/zsh
# Deploy push2HAL weel to pypi server.
set -x
# wheel path
WHEEL_DIR=$(pwd)/dist

function wheel()
{
    # Build and test wheel in an venv to check if all required files are present in
    # the wheel.
    # Clean-up previous version
    rm  $WHEEL_DIR/push2HAL*.whl
    pip3 wheel . -w dist
    # Setup venv
    TEMP_DIR=$(mktemp -d)
    python3 -m venv $TEMP_DIR
    source $TEMP_DIR/bin/activate
    # Change dir to test really wheel file and not the repo files
    cd $TEMP_DIR
    # Install the wheel
    pip3 install $WHEEL_DIR/push2HAL*.whl
    # Run all tests
    # python3 -m push2HAL.tests
    SUCCESS=$?
    # Clean-up tmp directory
    cd $WHEEL_DIR
    trap 'rm -rf "$TEMP_DIR"' EXIT
    deactivate
    python -V
    which python
    if [ $SUCCESS -eq 0 ]
    then
        echo "Ready for uploading :" $(ls $WHEEL_DIR/push2HAL*.whl)
        return 0
    else
        echo "Test failed. Stop deployment." >&2
        return 1
    fi
}

# Main deployment script
for i in "$@"
do
    case "$i" in
    -i|--install) pip install --user twine
    ;;
    -c|--check) which python&&python -V&&twine --version&&which twine
    ;;
    -t|--test)
    wheel && twine upload --verbose -r testpypi $WHEEL_DIR/push2HAL*.whl
    ;;
    -d|--deploy)
    wheel && twine upload --verbose $WHEEL_DIR/push2HAL*.whl
    ;;
    esac
done