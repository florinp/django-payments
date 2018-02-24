from __future__ import unicode_literals
import json
import braintree
from django.core.exceptions import ImproperlyConfigured

from .forms import BraintreePaymentForm
from .. import PaymentStatus, RedirectNeeded
from ..core import BasicProvider


class BraintreeProvider(BasicProvider):

    def __init__(self, merchant_id, public_key, private_key, sandbox=True,
                 **kwargs):
        self.merchant_id = merchant_id
        self.public_key = public_key
        self.private_key = private_key

        environment = braintree.Environment.Sandbox
        if not sandbox:
            environment = braintree.Environment.Production

        braintree.Configuration.configure(
            environment, merchant_id=self.merchant_id,
            public_key=self.public_key, private_key=self.private_key)
        super(BraintreeProvider, self).__init__(**kwargs)
        if not self._capture:
            raise ImproperlyConfigured(
                'Braintree does not support pre-authorization.')

    def get_form(self, payment, data=None):
        if payment.status == PaymentStatus.WAITING:
            payment.change_status(PaymentStatus.INPUT)
        form = BraintreePaymentForm(data=data, payment=payment, provider=self)
        if form.is_valid():
            form.save()
            raise RedirectNeeded(payment.get_success_url())
        return form

    def capture(self, payment, amount=None):
        pass

    def release(self, payment):
        result = braintree.Transaction.refund(payment.transaction_id)
        if result.is_success:
            payment.attrs.release = json.dumps(result.transaction)

    def refund(self, payment, amount=None):
        amount = str(amount or payment.total)
        result = braintree.Transaction.refund(payment.transaction_id)
        if result.is_success:
            payment.attrs.refund = json.dumps(payment.transaction)

        return Decimal(amount)
