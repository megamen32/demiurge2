import datetime
from typing import List

import peewee




class Prompt(peewee.Model):
    id= peewee.AutoField(primary_key=True)
    text= peewee.CharField(unique=True)
    class Meta:
        database=peewee.SqliteDatabase('promt.db')

class ImageMidjourney(peewee.Model):
    id= peewee.AutoField(primary_key=True)
    url= peewee.CharField(unique=True)
    prompt=peewee.CharField()
    def filename(self):
        return   self.url.split('/')[-1].split('?',1)[0]
    class Meta:
        database=peewee.SqliteDatabase('promt.db')

class ImageUnstability(peewee.Model):
    url= peewee.CharField(unique=True,primary_key=True)
    prompt=peewee.CharField()
    def filename(self):
        return   self.url.split('/')[-1].split('&',1)[0]
    class Meta:
        database=peewee.SqliteDatabase('promt.db')
from peewee import Model, CharField, IntegerField, SqliteDatabase, ForeignKeyField,DateTimeField,BooleanField
db = SqliteDatabase('users.db')
class User(Model):
    user_id = peewee.BigIntegerField(unique=True)
    username = CharField(null=True)
    created_at=DateTimeField(default=datetime.datetime.now)
    is_admin=BooleanField(default=False)
    is_gpt4=BooleanField(default=False)
    settings= peewee.TextField(default='[]')
    class Meta:
        database = db

class ModelUsage(Model):
    user = ForeignKeyField(User, backref='usages')
    model_name = CharField()  # Название модели (gpt3, gpt4, whisper, etc.)
    input_symbols = IntegerField(default=0)  # Входные символы
    output_symbols = IntegerField(default=0)  # Выходные символы

    class Meta:
        database = db
        indexes = ((('user', 'model_name'), True),)
def update_model_usage(user_id, model_name, input_len, output_len):
    user, _ = User.get_or_create(user_id=user_id)
    usage, _ = ModelUsage.get_or_create(user=user, model_name=model_name)
    usage.input_symbols += input_len
    usage.output_symbols += output_len
    usage.save()

model_prices = {
    "gpt-3.5-turbo":      {"input": 0.03, "output": 0.06},
    "gpt-3.5-turbo-0613": {"input": 0.03, "output": 0.06},
    "gpt-3.5-turbo-16k": {"input": 0.06, "output": 0.12},
    "gpt-3.5-turbo-16k-0613": {"input": 0.06, "output": 0.12},
    "gpt-4": {"input": 0.0015, "output": 0.002},
    "gpt-4-0613": {"input": 0.0015, "output": 0.002},
    "gpt-4-32k": {"input":  0.003, "output": 0.004},
    "gpt-4-32k-0613": {"input": 0.003, "output": 0.004},
    "Whisper": 0.006  # цена в минуту
}


async def get_rub_to_usd():
    return 95


async def get_user_balance(user_id,message):
    try:
        from telegrambot.handlers import create_user
        user = create_user( message,user_id)
        model_usages :List[ModelUsage]= ModelUsage.select().where(ModelUsage.user == user)
        payments = PaymentInfo.select().where(PaymentInfo.user_id == user_id)
        total_payments = sum([payment.amount for payment in payments])
        total_payments = total_payments/(await get_rub_to_usd())
        total_balance = total_payments
        balances = {}

        for model_usage in model_usages:
            model_name = model_usage.model_name
            if model_name in model_prices:
                price_info = model_prices[model_name]
                input_cost = model_usage.input_symbols / 1000 * price_info["input"]
                output_cost = model_usage.output_symbols / 1000 * price_info["output"]
                total_cost = input_cost + output_cost
                total_balance -= total_cost

                balances[model_name] = {
                    "input_chars": model_usage.input_symbols,
                    "output_chars": model_usage.output_symbols,
                    "total_cost": total_cost
                }

        return {"balances": balances, "total_balance": total_balance,'total_payments':total_payments}
    except User.DoesNotExist:
        return {"error": "User not found"}


class PaymentInfo(Model):
    user= ForeignKeyField(User,backref='payments')
    amount = peewee.FloatField()
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db