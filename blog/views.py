from django.shortcuts import render,redirect
from .models import Post, Sell, History ,rpcConfig
from django.contrib.auth.models import User,auth
from django.contrib import messages
from Savoir import Savoir
from datetime import datetime
from django.db.models import Count
from django.http import JsonResponse
import pytz
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.csrf import csrf_protect

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
    ttlprice = float(tenergy) * float(tprice)
    timestamp = datetime.now()
    print(username)                   
    print(tenergy)                                                                                                                                                  
    print(tprice)                                                                                                                                               
    print(timestamp)

    #Get firstname
    firstName = User.objects.filter(username=username).values_list('first_name')
    print(firstName[0][0])

    myBalance = getBalanceWallet(api)
    myEcoin = myBalance[0]
    myEnergy = myBalance[1]
    print(myEnergy)
    print(tenergy)
    if(int(myEnergy)>=int(tenergy)):
        res = api.preparelockunspent ({"energy": float(tenergy)})
        tblob = api.createrawexchange(res["txid"], res["vout"],{"ecoin": float(tprice)})

        #insert data into table Sell
        insertSell = Sell.objects.create(user=str(username), blob=str(tblob), energy=float(tenergy) ,price=float(tprice), ttlprice=float(ttlprice), timestamp=timestamp, fname=str(firstName[0][0]))
        insertSell.save()

        #insert data into table History
        insertHistory = History.objects.create(user=str(username), transection='Offer', energy=float(tenergy), price=float(tprice), ttlprice=float(ttlprice), timestamp=timestamp, blob=str(tblob), status='Pending', partner_name='Pending', txid='')
        insertHistory.save()

        messages.info(request,'Your offering is successful.')
    else:
        messages.info(request,'Your amount energy is not enough.')

    data=History.objects.filter(user=username, transection='Offer', status='Pending').all().order_by('status','-id')
    return render(request,'sell.html', {
        'posts':data,
        'power':myEnergy,
        'money':myEcoin,
        })

def buyMatch(request):
    unit = request.POST['unit']
    price = request.POST['price']
    ttlprice = float(unit)*float(price)
    timestamp = datetime.now()
    # print(unit)
    # print(price)
    username = request.user
    api = getApi(username)
    myBalance = getBalanceWallet(api)
    myCoin = myBalance[0]
    myPower = myBalance[1]

    #Get firstname
    firstName = User.objects.filter(username=username).values_list('first_name')
    buyName = str(firstName[0][0])
    print("Buy name :"+buyName)

    #Select Sell.blob from Sell where Sell.energy like unit and Sell.price like price
    listBlob=Sell.objects.filter(energy=float(unit), price=float(price)).values_list('blob', 'user', 'fname')
    if(len(listBlob)!=0):
        blob = listBlob[0][0]
        userBlob = listBlob[0][1]
        sellName = listBlob[0][2]

        print("Blob name :"+str(userBlob))
        print("Sell username :"+str(username))
        print("Sell name :"+str(sellName))
        print("Buy Energy :"+str(unit))
        print("Buy Price :"+str(price))
        print("Buy Total Price :"+str(ttlprice))

        #If coin not enough
        if(float(myCoin)>=float(price)):
            #If usersell is not login user
            if(str(userBlob)!=str(username)) :
                #match buy process
                res1 = api.preparelockunspent({"ecoin": float(ttlprice)})
                print(res1)
                res2 = api.appendrawexchange(str(blob), res1["txid"], res1["vout"],{"energy": float(unit)})
                print(res2)
                txid = str(api.sendrawtransaction(res2["hex"]))
                print(txid)

                #Update status blob with transection = sell
                updateStatus = History.objects.get(blob=str(blob))
                updateStatus.status = 'Sold out'  # change status
                updateStatus.txid = txid
                updateStatus.partner_name = buyName
                updateStatus.save() # this will update only

                #Insert transection buy with blob
                insertHistory = History.objects.create(user=str(username), transection='Bid', energy=float(unit), price=float(price), ttlprice=float(ttlprice), timestamp=timestamp, blob=str(blob), status='', partner_name=str(sellName), txid=txid)
                insertHistory.save()

                #Delete record blob = blob
                dBlob = Sell.objects.get(blob=blob)
                dBlob.delete()
                messages.info(request,'Your biding is successful.')
            else:
                messages.info(request,'Not found offering match with your biding.')                                                                     
        else:
            messages.info(request,'Your wallet is successful.')    
    else:
        messages.info(request,'Not found offering match with your biding.')   
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
    
    #1.Caculate Total Sell
    #1.1) #Caculate Total Sell -> Status pending
    totalPending=History.objects.filter(user=username, transection='Offer',status='Pending').values_list('energy', 'ttlprice')
    pendingEnergyList = []
    pendingPriceList = []
    rangeOfPendingList = int(len(totalPending))
    if(rangeOfPendingList != 0):
        for n in range(rangeOfPendingList):
            pendingEnergyList.append(totalPending[n][0])
            pendingPriceList.append(totalPending[n][1])
        totalPendingEnergy = sum(pendingEnergyList)   
        totalPendingPrice = sum(pendingPriceList)
    else:
        totalPendingEnergy = 0
        totalPendingPrice = 0
    #1.2) #Caculate Total Sell -> Status sold out
    totalSoldOut=History.objects.filter(user=username, transection='Offer',status='Sold out').values_list('energy', 'ttlprice')
    soldOutEnergyList = []
    soldOutPriceList = []
    rangeOfSoldOutList = int(len(totalSoldOut))
    if(rangeOfSoldOutList != 0):
        for n in range(rangeOfSoldOutList):
            soldOutEnergyList.append(totalSoldOut[n][0])
            soldOutPriceList.append(totalSoldOut[n][1])
        totalSoldOutEnergy = sum(soldOutEnergyList)   
        totalSoldOutPrice = sum(soldOutPriceList)         
    else:
        totalSoldOutEnergy = 0
        totalSoldOutPrice = 0      
    #1.3) #Caculate Total Sell -> Pending + Sold out
    totalSellEnergy = totalPendingEnergy + totalSoldOutEnergy
    totalSellPrice = totalPendingPrice + totalSoldOutPrice
    #1.4) #Create list sell
    sellList = [totalPendingEnergy, totalPendingPrice, totalSoldOutEnergy, totalSoldOutPrice, totalSellEnergy, totalSellPrice]

    #2.Caculate Total Buy
    #2.1) #Caculate Total Buy ->energy and price
    totalBuy=History.objects.filter(user=username, transection='Bid').values_list('energy', 'ttlprice')
    buyEnergyList = []
    buyPriceList = []
    rangeOfBuyList = int(len(totalBuy))
    for n in range(rangeOfBuyList):
        buyEnergyList.append(totalBuy[n][0])
        buyPriceList.append(totalBuy[n][1])
    totalBuyEnergy = sum(buyEnergyList)   
    totalBuyPrice = sum(buyPriceList)
    #2.2) #Create list buy
    buyList = [totalBuyEnergy, totalBuyPrice]

    #3.select history
    data=History.objects.filter(user=username).all().order_by('-id')
    
    return render(request,'index.html',
    {
        'posts':data,
        'power':energy,
        'money':ecoin,
        'pendingEnergy':totalPendingEnergy,
        'pendingPrice':totalPendingPrice,
        'soldOutEnergy':totalSoldOutEnergy,
        'soldOutPrice':totalSoldOutPrice,
        'sellEnergy':totalSellEnergy,
        'sellPrice':totalSellPrice,
        'buyEnergy':totalBuyEnergy,
        'buyPrice':totalBuyPrice
    })

def form(request):
    return render(request,'form.html')

def topUp(request):
    return render(request,'topUp.html')

def deposit(request):
    return render(request,'deposit.html')
    
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
        messages.info(request,"That ccount doesn't exist. Enter a different account or register")
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
    data=History.objects.filter(user=username, transection='Offer', status='Pending').all().order_by('status','-id')
    # count=History.objects.filter(user=username, transection='Sell', status='Selling').all().values('price').annotate(total=Count('price'))
    return render(request,'sell.html',{
        'posts':data,
        'power':energy,
        'money':ecoin,
        })

@csrf_protect
def calcualtePriceSellAmount(request) :
    unit_amount = request.headers.get('unitAmount')
    price_amount = request.headers.get('priceAmount')
    print("Unit : "+unit_amount)
    print("Price : "+price_amount)
    if(len(unit_amount) != 0 and len(price_amount) != 0):
        sell_price = float(unit_amount) * float(price_amount)
        print("total : "+str(float(sell_price)))
        response = JsonResponse(status = 200 , data = { 'sellPrice' : sell_price })
        response.status_code = 200
        return response
    elif(len(unit_amount) != 0 and len(price_amount) == 0):
        sell_price = float(unit_amount) * 1.00
        response = JsonResponse(status = 200 , data = { 'sellPrice' : sell_price })
        response.status_code = 200
        return response
    else:
        response = JsonResponse(status = 200 , data = { 'sellPrice' : 0.00 })
        response.status_code = 200
        return response