from typing import Callable, Dict, Any, Optional
import json
import logging
from ..common.exceptions import KafkaError
from ..config.settings import settings

logger = logging.getLogger(__name__)


class KafkaConsumer:
    """
    Kafka consumer for processing events.
    Handles subscription, polling, and message processing.
    """
    
    def __init__(self, topics: list[str], group_id: Optional[str] = None):
        self.topics = topics
        self.group_id = group_id or settings.KAFKA_GROUP_ID
        self._consumer = None
        self._handlers: Dict[str, Callable] = {}
        self._initialize_consumer()
    
    def _initialize_consumer(self):
        """Initialize Kafka consumer."""
        # Skip initialization if Kafka is disabled
        if not settings.KAFKA_ENABLED:
            logger.warning("Kafka is disabled (KAFKA_ENABLED=false), consumer will not be initialized")
            self._consumer = None
            return

        try:
            from confluent_kafka import Consumer as ConfluentConsumer
            
            config = {
                'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
                'group.id': self.group_id,
                'auto.offset.reset': settings.KAFKA_AUTO_OFFSET_RESET,
                'enable.auto.commit': True,
                'session.timeout.ms': 10000,
                'heartbeat.interval.ms': 3000
            }
            
            self._consumer = ConfluentConsumer(config)
            self._consumer.subscribe(self.topics)
            
            logger.info(f"Kafka consumer initialized for topics: {self.topics}")
            
        except ImportError:
            raise KafkaError("confluent-kafka package not installed")
        except Exception as e:
            raise KafkaError(f"Failed to initialize Kafka consumer: {str(e)}")
    
    def register_handler(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        """
        Register a handler for a specific event type.
        
        Args:
            event_type: Type of event to handle (e.g., "ResumeUploaded")
            handler: Function to call when event is received
        """
        self._handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")
    
    def start_consuming(self, poll_timeout: float = 1.0):
        """
        Start consuming messages from Kafka.
        
        Args:
            poll_timeout: Timeout in seconds for polling
        """
        # If Kafka is disabled, log warning and return
        if not settings.KAFKA_ENABLED:
            logger.warning("Kafka is disabled (KAFKA_ENABLED=false), skipping consumer start")
            return

        logger.info("Starting Kafka consumer...")
        
        try:
            while True:
                msg = self._consumer.poll(timeout=poll_timeout)
                
                if msg is None:
                    continue
                
                if msg.error():
                    logger.error(f"Consumer error: {msg.error()}")
                    continue
                
                try:
                    self._process_message(msg)
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}", exc_info=True)
                    
        except KeyboardInterrupt:
            logger.info("Consumer stopped by user")
        except Exception as e:
            logger.error(f"Consumer error: {str(e)}", exc_info=True)
            raise KafkaError(f"Consumer error: {str(e)}")
        finally:
            self.close()
    
    def _process_message(self, msg):
        """Process a single Kafka message."""
        try:
            # Deserialize message
            value = json.loads(msg.value().decode('utf-8'))
            
            event_type = value.get('event_type')
            payload = value.get('payload')
            
            if not event_type:
                logger.warning(f"Message missing event_type: {msg.topic()}")
                return
            
            # Find and call handler
            handler = self._handlers.get(event_type)
            if handler:
                logger.info(f"Processing event {event_type} from topic {msg.topic()}")
                handler(payload)
            else:
                logger.warning(f"No handler registered for event type: {event_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize message: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
    
    def close(self):
        """Close the consumer connection."""
        if self._consumer:
            self._consumer.close()
            logger.info("Kafka consumer closed")
