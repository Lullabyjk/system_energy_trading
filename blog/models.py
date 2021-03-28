from django.db import models

# Create your models here.
class Post(models.Model):
    name=models.CharField(max_length=200)
    desc=models.TextField()

class Post1(models.Model):
    name=models.CharField(max_length=200)
    desc=models.TextField()

class Sell(models.Model):
    user=models.CharField(max_length=200)
    fname=models.CharField(max_length=200)
    blob=models.TextField()
    energy=models.IntegerField()
    price=models.IntegerField()
    ttlprice=models.IntegerField()
    timestamp =models.DateTimeField()

class History(models.Model):
    user=models.CharField(max_length=200)
    blob=models.TextField()
    transection=models.TextField()
    energy=models.IntegerField()
    price=models.IntegerField()
    ttlprice=models.IntegerField()
    timestamp=models.DateTimeField()
    status=models.CharField(max_length=200)
    partner_name=models.CharField(max_length=200)
    txid=models.TextField()

class rpcConfig(models.Model):
    username=models.CharField(max_length=200)
    rpc_password=models.CharField(max_length=200)
    rpc_host=models.CharField(max_length=200)





