from pybiz.app.middleware import Guard


class HistoryExists(Guard):
    """
    # History Guard
    """

    def execute(self, context, history):
        if not history:
            return False
        return True
