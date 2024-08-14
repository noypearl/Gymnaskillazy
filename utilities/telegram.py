from telegram.ext.filters import MessageFilter

class NumericOrDotFilter(MessageFilter):
    def filter(self, message):
        msg = message.text.strip()
        return msg.isdigit() or msg == '.'
