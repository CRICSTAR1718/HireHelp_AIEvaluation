from typing import Dict, Any, Optional
import json
import logging
from ..common.exceptions import KafkaError
from ..config.settings import settings

logger = logging.getLogger(__name__)


class KafkaProducer:
    """
    Kafka producer for publishing events.
    Handles serialization and error handling.
    """
    
    def __init__(self):
        self._producer = None
        self._initialize_producer()
    
    def _initialize_producer(self):
        """Initialize Kafka producer."""
        # Skip initialization if Kafka is disabled
        if not settings.KAFKA_ENABLED:
            logger.warning("Kafka is disabled (KAFKA_ENABLED=false), producer will not be initialized")
            self._producer = None
            return

        try:
            from confluent_kafka import Producer as ConfluentProducer
            
            config = {
                'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
                'client.id': 'ai-evaluation-service-producer',
                'acks': 'all',
                'retries': 3,
                'delivery.timeout.ms': 10000
            }
            
            self._producer = ConfluentProducer(config)
            logger.info("Kafka producer initialized")
            
        except ImportError:
            raise KafkaError("confluent-kafka package not installed")
        except Exception as e:
            raise KafkaError(f"Failed to initialize Kafka producer: {str(e)}")
    
    def publish_event(
        self,
        topic: str,
        event_type: str,
        payload: Dict[str, Any],
        key: Optional[str] = None
    ) -> bool:
        """
        Publish an event to Kafka.
        
        Args:
            topic: Kafka topic name
            event_type: Type of event (e.g., "ResumeParsed")
            payload: Event data
            key: Optional partition key
        
        Returns:
            True if published successfully (or logged when disabled)
        """
        # If Kafka is disabled, log what would have been published
        if not settings.KAFKA_ENABLED:
            event = {
                "event_type": event_type,
                "timestamp": self._get_timestamp(),
                "payload": payload
            }
            logger.info(
                f"Kafka disabled - would publish event {event_type} to topic {topic}. "
                f"Payload: {json.dumps(event)}"
            )
            return True
        
        if not self._producer:
            logger.warning("Kafka producer not initialized, skipping event publish")
            return False
        
        try:
            event = {
                "event_type": event_type,
                "timestamp": self._get_timestamp(),
                "payload": payload
            }
            
            value = json.dumps(event).encode('utf-8')
            key_bytes = key.encode('utf-8') if key else None
            
            # Callback for delivery report
            def delivery_report(err, msg):
                if err:
                    logger.error(f"Message delivery failed: {err}")
                else:
                    logger.debug(
                        f"Message delivered to {msg.topic()} [{msg.partition()}] "
                        f"at offset {msg.offset()}"
                    )
            
            self._producer.produce(
                topic=topic,
                key=key_bytes,
                value=value,
                callback=delivery_report
            )
            
            # Flush to ensure message is sent
            self._producer.flush(timeout=5.0)
            
            logger.info(f"Published event {event_type} to topic {topic}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event: {str(e)}")
            raise KafkaError(f"Failed to publish event: {str(e)}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'
    
    def close(self):
        """Close the producer connection."""
        if self._producer:
            self._producer.flush()
            logger.info("Kafka producer closed")


# Singleton instance
_producer_instance: Optional[KafkaProducer] = None


def get_kafka_producer() -> KafkaProducer:
    """Get or create the singleton Kafka producer instance."""
    global _producer_instance
    if _producer_instance is None:
        _producer_instance = KafkaProducer()
    return _producer_instance
