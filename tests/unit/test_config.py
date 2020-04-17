import pathlib

import pytest
from marshmallow import Schema, ValidationError, fields

from relay.config.config import (
    _remove_empty_dicts,
    generate_default_config,
    load_config,
    validation_error_string,
)


class NestedSchema(Schema):
    a_string = fields.String(required=True)


class TestSchema(Schema):
    an_int = fields.Integer(required=True)
    nested = fields.Nested(NestedSchema)


@pytest.fixture()
def example_config_filepath():
    return str(
        pathlib.Path(__file__).parent.parent.parent.joinpath("config.toml").absolute()
    )


@pytest.fixture()
def uncommented_example_config_filepath(example_config_filepath, tmp_path):
    # Remove all comments starting with only one # to test of that config is correct
    d = tmp_path / "example.conf"

    with open(example_config_filepath) as file:
        with open(d, "w") as output_file:
            for line in file.readlines():
                output_file.writelines([line.replace("# ", " ")])

    return str(d)


@pytest.fixture()
def correct_fees_config_file(tmp_path):
    folder = tmp_path / "subfolder"
    folder.mkdir()
    file_path = folder / "correct_config.toml"
    file_path.write_text(
        "\n".join(
            (
                "[delegate]",
                "enable = true",
                "enable_deploy_identity = true",
                "fees=[{'base_fee'=0, 'gas_price'=0}]",
            )
        )
    )
    return file_path


@pytest.mark.parametrize(
    "test_input, expected_output",
    [
        ({}, {}),
        ({"something": {}}, {}),
        ({"test": None, "deeper": {"nested": {}, "none": None}}, {}),
        (
            {"test": None, "deeper": {"nested": {}, "none": None, "value": 5}},
            {"deeper": {"value": 5}},
        ),
    ],
)
def test_remove_empty_dicts(test_input, expected_output):
    assert _remove_empty_dicts(test_input) == expected_output


def test_example_file_matches_default_config(example_config_filepath):
    """Test that the example config matches the default config"""
    assert load_config(example_config_filepath) == generate_default_config()


def test_uncommented_default_config_is_valid(uncommented_example_config_filepath):
    """ Test that if you uncomment the not default fields, that the config is valid"""
    load_config(uncommented_example_config_filepath)


def test_correct_fee_config_is_valid(correct_fees_config_file):
    load_config(correct_fees_config_file)


def test_validation_error_message():
    error_message = ""
    try:
        TestSchema().load({"an_int": "Not an int", "nested": {"a_string": 5}})
    except ValidationError as e:
        error_message = validation_error_string(e)

    messages = [
        ".nested.a_string: Not a valid string.",
        ".an_int: Not a valid integer.",
    ]
    assert error_message == ", ".join(messages) or error_message == ", ".join(
        reversed(messages)
    )
