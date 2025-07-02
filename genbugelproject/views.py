from django.shortcuts import render

def home(request):
    return render(request, 'index.html')

#def login_view(request):
    #return render(request, 'login.html')

def signup_view(request):
    return render(request, 'signup.html')



#def frontpage(request):  # 👈 ADD THIS HERE
    #return render(request, 'frontpage.html')




