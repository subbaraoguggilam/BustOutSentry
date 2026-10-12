import json
import time
from kafka import KafkaProducer


producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda value: json.dumps(value).encode("utf-8")
)


def send_transaction(transaction):

    producer.send(
        "transactions",
        value=transaction
    )

    producer.flush()

    print("Transaction sent:")
    print(transaction)


if __name__ == "__main__":

    transactions = [

        {
            "customer_id": "C00004",
            "transaction_id": "TXN001",
            "amount": 4500,
            "merchant_category": "cash_advance",
            "mcc": 6011,
            "terminal_type": "POS",
            "payment_source": "third_party",
            "payment_verified": 0
        },

        {
            "customer_id": "C00004",
            "transaction_id": "TXN002",
            "amount": 3800,
            "merchant_category": "cash_advance",
            "mcc": 6011,
            "terminal_type": "POS",
            "payment_source": "third_party",
            "payment_verified": 0
        },

        {
            "customer_id": "C00004",
            "transaction_id": "TXN003",
            "amount": 5200,
            "merchant_category": "money_transfer",
            "mcc": 4829,
            "terminal_type": "POS",
            "payment_source": "third_party",
            "payment_verified": 0
        }
    ]

    for transaction in transactions:

        send_transaction(transaction)

        time.sleep(2)