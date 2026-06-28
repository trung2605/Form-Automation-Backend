import time
from flask import current_app
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from payos import PayOS
from payos.types import ItemData, CreatePaymentLinkRequest

PACKAGES = {
    'starter': {'price': 50000, 'credits': 500},
    'pro': {'price': 200000, 'credits': 2500},
    'enterprise': {'price': 500000, 'credits': 7500}
}

class PaymentService:
    @staticmethod
    def get_payos():
        return PayOS(
            client_id=current_app.config['PAYOS_CLIENT_ID'] or "",
            api_key=current_app.config['PAYOS_API_KEY'] or "",
            checksum_key=current_app.config['PAYOS_CHECKSUM_KEY'] or ""
        )

    @staticmethod
    def create_payment_link(user_id, package_id, custom_credits):
        credits = custom_credits
        
        if package_id and package_id in PACKAGES:
            price = PACKAGES[package_id]['price']
            credits = PACKAGES[package_id]['credits']
        elif credits > 0:
            price = credits * 100
        else:
            return {"error": "Yêu cầu không hợp lệ"}, 400

        wallet = Wallet.objects(user_id=user_id).first()
        if not wallet:
            return {"error": "Ví không tồn tại"}, 404
        
        # PayOS requires amount >= 2000 VND
        if price < 2000:
            return {"error": "Số tiền thanh toán tối thiểu là 2000 VNĐ"}, 400

        order_code = int(time.time() * 1000) % 9007199254740991 # Max integer safe for JS/PayOS
        
        # Create pending transaction
        tx = Transaction(
            user_id=user_id,
            amount=credits,
            order_code=order_code,
            transaction_type='deposit',
            status='pending',
            description=f'Nạp {credits} credits'
        )
        tx.save()

        payos = PaymentService.get_payos()
        
        try:
            # Create payment data
            payment_data = CreatePaymentLinkRequest(
                orderCode=order_code,
                amount=price,
                description=f"Nap {credits} cr", # Max 25 chars
                items=[ItemData(name=f"{credits} Credits", quantity=1, price=price)],
                returnUrl="http://localhost:3000/wallet?status=success",
                cancelUrl="http://localhost:3000/wallet?status=cancelled"
            )
            
            payos_checkout = payos.payment_requests.create(payment_data)
            
            return {
                "checkoutUrl": payos_checkout.checkoutUrl,
                "orderCode": order_code
            }, 200
            
        except Exception as e:
            print(f"PayOS Error: {str(e)}")
            # Delete pending transaction if failed to create link
            tx.delete()
            return {"error": "Lỗi khi tạo mã thanh toán: " + str(e)}, 500

    @staticmethod
    def process_webhook(webhook_data):
        payos = PaymentService.get_payos()
        
        try:
            verified_data = payos.verifyPaymentWebhookData(webhook_data)
            
            if verified_data.code == "00" or webhook_data.get("success") == True:
                # Payment successful
                order_code = verified_data.orderCode
                
                # Find the transaction
                tx = Transaction.objects(order_code=order_code).first()
                if tx and tx.status == 'pending':
                    tx.status = 'completed'
                    tx.save()
                    
                    # Update wallet balance
                    wallet = Wallet.objects(user_id=tx.user_id).first()
                    if wallet:
                        wallet.balance += tx.amount
                        wallet.save()
                        
            return {"error": 0, "message": "Ok", "data": None}, 200
            
        except Exception as e:
            print("Webhook Verification Error:", e)
            return {"error": 1, "message": str(e)}, 400

    @staticmethod
    def get_user_transactions(user_id):
        txs = Transaction.objects(user_id=user_id).order_by('-created_at').limit(50)
        
        result = []
        for tx in txs:
            result.append({
                "id": str(tx.id),
                "amount": tx.amount,
                "type": tx.transaction_type,
                "status": tx.status,
                "description": tx.description,
                "created_at": tx.created_at.isoformat()
            })
            
        return result, 200
