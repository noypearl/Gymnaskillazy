from utilities.collections import neutralize_str


class InputValidation:

    @staticmethod
    def digit_or_dot(message: str):
        msg = message.strip()
        return msg.isdigit() or msg == '.'

    @staticmethod
    def accepted_value(value: str, expected_values: list) -> bool:
        value = value.strip()
        return neutralize_str(value) in list(map(neutralize_str, expected_values))
