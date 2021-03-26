from django.shortcuts import render,redirect
from .models import Post, Sell, History ,rpcConfig
from django.contrib.auth.models import User,auth
from django.contrib import messages
from Savoir import Savoir
from datetime import datetime
from django.db.models import Count
import pytz

##Set time zone bangkok
tz = pytz.timezone('Asia/Bangkok')
def getApi(username):
    #username = 'intouch12345'
    rpc_config=rpcConfig.objects.filter(username=username).values_list('rpc_password', flat=True)[0]
    print(rpc_config)
    rpcuser = 'multichainrpc'
    rpcpasswd = rpc_config
    rpchost = rpcConfig.objects.filter(username=username).values_list('rpc_host', flat=True)[0]
    rpcport = '4392'
    chainname = 'energytd'
    api = Savoir(rpcuser, rpcpasswd, rpchost, rpcport, chainname)
    return api


 
#Get balance of Power
def getBalanceWallet(api):
    #nodeaddress = api.getinfo()["nodeaddress"]
    ##print(nodeaddress)
    for address in api.listaddresses():
        if address.get("ismine") == True:
            address = address.get("address")
    listBalance = api.getmultibalances()['total']
    ##Check balance of ecoin and energy
    myList = []
    ##Have only [ecoin or energy]
    if len(listBalance) == 1:
            if listBalance[0]['name'] == 'ecoin':
                    myList.insert(0, api.getmultibalances()[address][0].get('qty'))
                    myList.insert(1, 0)
            else:
                    myList.insert(0, 0)
                    myList.insert(1, api.getmultibalances()[address][0].get('qty'))
    ##Have both [ecoin and energy]
    else:
            if listBalance[0]['name'] == 'ecoin':
                    myList.insert(0, api.getmultibalances()[address][0].get('qty'))
                    myList.insert(1, api.getmultibalances()[address][1].get('qty'))
            else:
                    myList.insert(0, api.getmultibalances()[address][1].get('qty'))
                    myList.insert(1, api.getmultibalances()[address][0].get('qty'))  
    ##myList = [ ecoin, energy]
    return myList                                                                                                                                                                                                                      
                                                                                                                                                                                                                                                                                                    
def sellForm(request):    
    
    ##Get current username
    username = request.user    
    api = getApi(username)                                                                                                           
    tenergy = request.POST['unit']                                          
    tprice = request.POST['price']
    timestamp = datetime.now()
    print(username)                   
    print(tenergy)                                                                                                                                                  
    print(tprice)                                                                                                                                               
    print(timestamp)

    myBalance = getBalanceWallet(api)
    myEcoin = myBalance[0]
    myEnergy = myBalance[1]
    print(myEnergy)
    print(tenergy)
    if(int(myEnergy)>=int(tenergy)):
        res = api.preparelockunspent ({"energy": int(tenergy)})
        tblob = api.createrawexchange(res["txid"], res["vout"],{"ecoin": int(tprice)})

        #insert data into table Sell
        insertSell = Sell.objects.create(user=str(username), blob=str(tblob), energy=tenergy ,price=tprice, timestamp=timestamp)
        insertSell.save()

        #insert data into table History
        insertHistory = History.objects.create(user=str(username), transection='Sell', energy=tenergy, price=tprice, timestamp=timestamp, blob=str(tblob), status='Selling')
        insertHistory.save()

        messages.info(request,'ลงขายสำเร็จ')
    else:
        messages.info(request,'จำนวนพลังงานของคุณไม่เพียงพอ')

    data=History.objects.filter(user=username, transection='Sell').all()
    return render(request,'sell.html', {
        'posts':data,
        'power':myEnergy,
        'money':myEcoin,
        })

def buyMatch(request):
    
    unit = request.POST['unit']
    price = request.POST['price']
    timestamp = datetime.now()
    # print(unit)
    # print(price)
    username = request.user
    api = getApi(username)
    myBalance = getBalanceWallet(api)
    myCoin = myBalance[0]
    myPower = myBalance[1]

    #Select Sell.blob from Sell where Sell.energy like unit and Sell.price like price
    listBlob=Sell.objects.filter(energy=int(unit), price=int(price)).values_list('blob', 'user')
    if(len(listBlob)!=0):
        blob = listBlob[0][0]
        userBlob = listBlob[0][1]
        print(userBlob)
        print(username)

        
        print(myCoin)
        print(myPower)
        if(int(myCoin)>=int(price)):
            if(str(userBlob)!=str(username)) :

                #match buy
                res1 = api.preparelockunspent({"ecoin": int(price)})
                print(res1)
                res2 = api.appendrawexchange(str(blob), res1["txid"], res1["vout"],{"energy": int(unit)})
                print(res2)
                txid = api.sendrawtransaction(res2["hex"])
                print(txid)

                #Update status blob with transection = sell
                updateStatus = History.objects.get(blob=str(blob))
                updateStatus.status = 'Sold out'  # change status
                updateStatus.save() # this will update only

                #Insert transection buy with blob
                insertHistory = History.objects.create(user=str(username), transection='Buy', energy=unit, price=price, timestamp=timestamp, blob=str(blob), status='')
                insertHistory.save()

                #Delete record blob = blob
                dBlob = Sell.objects.get(blob=blob)
                dBlob.delete()
                messages.info(request,'ซื้อสำเร็จ')
            else:
                messages.info(request,'ขณะนี้ไม่พบผู้ขายที่ตรงกับความต้องการของคุณ')                                                                     
        else:
            messages.info(request,'ยอดเงินคงเหลือของคุณไม่เพียงพอ')    
    else:
        messages.info(request,'ขณะนี้ไม่พบผู้ขายที่ตรงกับความต้องการของคุณ')   
    data=Sell.objects.all().exclude(user=username)
    return render(request,'buy.html', {
        'posts':data,
        'power':myPower
        })

# Create your views here.
def home(request):
    username = request.user   
    api = getApi(username)
    myWallet = getBalanceWallet(api)
    energy = myWallet[1]
    ecoin = myWallet[0]
    # Query Data From Model.

    #Select * from History
    #data=History.objects.all()
    #Select desc from History where user like 'John'
    #data=History.objects.filter(user='John').values_list('desc', flat=True)
    #Select * from History where user like 'John'
    data=History.objects.filter(user=username).all()
    
    #data2=Sell.objects.values('blob')
    #data3=Sell.objects.values_list('blob', flat=True)
    #print(data2)
    #print(data3[0])

    return render(request,'index.html',
    {
        'posts':data,
        'power':energy,
        'money':ecoin,
    })

def form(request):
    return render(request,'form.html')

def aiAuanNook(request):
    return render(request,'aiAuanNook.html')

def login(request):
    return render(request,'login.html')

def mainForm(request):
    return render(request,'main.html')

def info(request):
    return render(request,'info.html')

def addUser(request):
    username = request.POST['username']
    firstname = request.POST['firstname']
    lastname = request.POST['lastname']
    email = request.POST['email']
    password = request.POST['password']
    repassword = request.POST['repassword']
    rpcpassword = request.POST['rpcpassword']

    if password == repassword :
        if User.objects.filter(username=username).exists():
            messages.info(request,'Username นี้มีคนใช้แล้ว')
            return redirect('/register')
        elif User.objects.filter(email=email).exists():
            messages.info(request,'Email นี้เคยลงทะเบียนแล้ว')
            return redirect('/register')
        elif username == '':
            messages.info(request,'กรุณากรอก Username')
            return redirect('/register')
        elif firstname == '':
            messages.info(request,'กรุณากรอก firstname')
            return redirect('/register')
        elif lastname == '':
            messages.info(request,'กรุณากรอก lastname')
            return redirect('/register')
        elif email == '':
            messages.info(request,'กรุณากรอก email')
            return redirect('/register')
        elif password == '':
            messages.info(request,'กรุณากรอก password')
            return redirect('/register')
        else :
            user = User.objects.create_user(
                    username=username,
                    password=password,
                    email=email,
                    first_name=firstname,
                    last_name=lastname,
                )
            user.save()
            rpcconfig = rpcConfig.objects.create(
                    username=username,
                    rpc_password=rpcpassword
                )
            rpcconfig.save()

            # add = Post1.objects.create(name=username)
            # add.save()
            return redirect('/login')
    else :
        messages.info(request,'Password ไม่ตรงกัน')
        return redirect('/register')

def loginForm(request):
    username = request.POST['username']
    password = request.POST['password']

    #check username,password
    user=auth.authenticate(username=username,password=password)

    if user is not None:
        auth.login(request,user)
        return redirect('/home')
    else :
        messages.info(request,'ไม่พบข้อมูล')
        return redirect('/login')

def logout(request):
    auth.logout(request)
    return redirect('/')

def buy(request):
    username = request.user  
    api = getApi(username)
    myWallet = getBalanceWallet(api)
    energy = myWallet[1]
    data=Sell.objects.all().exclude(user=username)
    return render(request,'buy.html', {
        'posts':data,
        'power':energy
        })

# def sell(request):
#     return render(request,'sell.html')

def sell(request):
    username = request.user   
    api = getApi(username)
    myWallet = getBalanceWallet(api)
    energy = myWallet[1]
    ecoin = myWallet[0]
    data=History.objects.filter(user=username, transection='Sell', status='Selling').all()
    # count=History.objects.filter(user=username, transection='Sell', status='Selling').all().values('price').annotate(total=Count('price'))
    return render(request,'sell.html',{
        'posts':data,
        'power':energy,
        'money':ecoin,
        })