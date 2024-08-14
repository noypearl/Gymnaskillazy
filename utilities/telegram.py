class InputValidation:

    @staticmethod
    def digit_or_dot(message: str):
        msg = message.strip()
        return msg.isdigit() or msg == '.'
