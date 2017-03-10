import asyncio


class BaseClient:
    def __init__(self, config_file: str):
        """
        Client init.

        :param config_file: Config file path.
        """
        self.loop = None

    def run_task(self, task, *args, **kwargs):
        """
        Run a given task injecting client as first parameter.

        :param task: Task to be executed.
        :param args: Task args.
        :param kwargs: Task kwargs.
        :return:
        """
        self.loop = asyncio.get_event_loop()
        return self.loop.run_until_complete(asyncio.ensure_future(task(self, *args, **kwargs), loop=self.loop))
