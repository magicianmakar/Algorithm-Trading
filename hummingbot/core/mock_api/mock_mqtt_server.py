from typing import Any, Dict

import ujson


class FakeMQTTMessage(object):
    def __init__(self,
                 topic,
                 payload):
        self.topic = topic
        fake_payload = {
            'header': {
                'reply_to': f"test_reply/{topic}"
            },
            'data': payload
        }
        self.payload = ujson.dumps(fake_payload)


class FakeMQTTBroker:
    def __init__(self):
        self._transport = None

    def create_transport(self, *args, **kwargs):
        if not self._transport:
            self._transport = FakeMQTTTransport(*args, **kwargs)
        return self._transport

    def publish_to_subscription(self, topic, payload):
        callback = self._transport._subscriptions[topic]
        msg = FakeMQTTMessage(topic=topic, payload=payload)
        callback(client=None,
                 userdata=None,
                 msg=msg)

    @property
    def subscriptions(self):
        return self._transport._subscriptions

    @property
    def received_msgs(self):
        return self._transport._received_msgs


class FakeMQTTTransport:

    def __init__(self, *args, **kwargs):
        self._subscriptions = {}
        self._received_msgs = {}
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    # def on_connect(self, *args, **kwargs):
    #     pass

    # def on_disconnect(self, *args, **kwargs):
    #     pass

    # def on_message(self, *args, **kwargs):
    #     pass

    def publish(self, topic: str, payload: Dict[str, Any], qos: Any, retain: bool = False):
        print(f"\nFakeMQTT publish on\n> {topic}\n     {payload}\n")
        if not self._received_msgs.get(topic):
            self._received_msgs[topic] = []
        self._received_msgs[topic].append(payload)

    def subscribe(self, topic: str, callback: Any, *args, **kwargs):
        self._subscriptions[topic] = callback
        return topic

    def start(self):
        self._connected = True

    def stop(self):
        self._connected = False

    def loop_forever(self):
        self.start()
