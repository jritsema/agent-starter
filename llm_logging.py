from typing import Any
from strands.hooks import HookProvider, HookRegistry
from strands.experimental.hooks import BeforeModelInvocationEvent
import logging
import json


class LoggingHookProvider(HookProvider):

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeModelInvocationEvent, self.log_input)

    def log_input(self, event: BeforeModelInvocationEvent) -> None:
        logging.info("BeforeModelInvocationEvent")
        logging.warning(json.dumps(event.agent.messages, indent=2))
