import json

from kafka import KafkaConsumer


consumer = KafkaConsumer(
    "transactions",
    bootstrap_servers="localhost:9092",
    group_id="bustoutsentry-scoring",
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    value_deserializer=lambda value: json.loads(
        value.decode("utf-8")
    )
)


print("BustOutSentry Kafka Consumer Started...")
print("Waiting for transactions...\n")


for message in consumer:

    transaction = message.value

    print("================================")
    print("NEW TRANSACTION")
    print("================================")

    print("Customer:", transaction["customer_id"])
    print("Transaction:", transaction["transaction_id"])
    print("Amount:", transaction["amount"])
    print("Merchant:", transaction["merchant_category"])
    print("Terminal:", transaction["terminal_type"])
    print("Payment Source:", transaction["payment_source"])
    print("Verified:", transaction["payment_verified"])

    print()