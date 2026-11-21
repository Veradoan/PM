from django.shortcuts import render,redirect
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.forms import AuthenticationForm
from .forms import UserRegisterForm
from django.http import HttpResponse
from django.contrib import messages
from .models import Country
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import CustomUser

# Create your views here.
def register_view(request):
    if request.method=='POST':
        form = UserRegisterForm(request.POST,request.FILES)
        print("POST:", request.POST)
        print("FORM VALID:", form.is_valid())
        print("FORM ERRORS:", form.errors)
        if form.is_valid():
            username = request.POST.get('username', '').strip() or form.cleaned_data['email']
            if CustomUser.objects.filter(username__iexact=username).exists():
                messages.error(request, 'Username đã tồn tại.')
                return render(request, 'user/register.html', {'form': form})
            user = form.save(commit=False)
            user.username = username
            user.set_password(form.cleaned_data['password'])
            user.is_superuser = False
            user.is_staff = False
            user.save()
            messages.success(request, 'Dang ky thanh cong!')
            return redirect('login')
        else:
            messages.error(request, 'Dang ky that bai!')
    else:
        form = UserRegisterForm()
    return render(request, 'user/register.html',{'form': form})
    
def login_view(request):
    if request.method == 'POST':
        # Lấy giá trị người dùng nhập vào từ ô input có name="username"
        identifier = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = None
        # Kiểm tra xem người dùng nhập vào là Email hay Username để xác thực chính xác
        if '@' in identifier:
            # Không phân biệt hoa/thường; nếu trùng email thì thử lần lượt từng tài khoản
            for matched_user in CustomUser.objects.filter(email__iexact=identifier):
                user = authenticate(request, username=matched_user.username, password=password)
                if user is not None:
                    break
        else:
            user = authenticate(request, username=identifier, password=password)

        if user is not None:
            login(request, user)
            return redirect('document_list')

        messages.error(request, 'Username/Email hoặc mật khẩu không đúng.')

    return render(request, 'user/login.html')
def logout_view(request):
    logout(request)
    return  redirect('login')

@login_required
def account_view(request):
    if request.method == "POST":
        user = request.user
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')

        user.city = request.POST.get('city')
        user.phone = request.POST.get('phone')

        country_id = request.POST.get('id_country')
        if country_id:
            user.id_country_id = country_id

        if request.FILES.get('avatar'):
            user.avatar = request.FILES.get('avatar')

        user.save()

        return redirect('account')
    return render(request, 'User/account.html',{'user_data': request.user,'countries': Country.objects.all()})

def forgot_password_view(request):

    if request.method == 'POST':

        email = request.POST.get('email', '').strip()

        try:
            user = CustomUser.objects.get(email=email)

            uid = urlsafe_base64_encode(
                force_bytes(user.pk)
            )

            token = default_token_generator.make_token(user)

            reset_link = request.build_absolute_uri(
                f'/User/reset-password/{uid}/{token}/'
            )

            subject = 'Reset your password'

            context = {
                'user': user,
                'reset_link': reset_link,
            }

            # Nội dung văn bản (dự phòng) + nội dung HTML
            text_content = render_to_string(
                'User/password-reset-email.html',
                context
            )
            html_content = render_to_string(
                'emails/password_reset_email.html',
                context
            )

            msg = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )
            msg.attach_alternative(html_content, 'text/html')

            print('EMAIL BACKEND:', settings.EMAIL_BACKEND, '| TO:', user.email)  # chẩn đoán, có thể xóa sau
            try:
                msg.send(fail_silently=False)
            except Exception as exc:
                print('EMAIL ERROR:', repr(exc))
                messages.error(
                    request,
                    'Không gửi được email. Vui lòng kiểm tra cấu hình email của server.'
                )
                return render(
                    request,
                    'User/forgot-password.html'
                )

            messages.success(
                request,
                'Email đổi mật khẩu đã được gửi. Hãy kiểm tra email của bạn.'
            )

        except CustomUser.DoesNotExist:

            messages.error(
                request,
                'Email này không tồn tại.'
            )

    return render(
        request,
        'User/forgot-password.html'
    )

def reset_password_view(request, uidb64, token):

    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):

        messages.error(
            request,
            'Link đổi mật khẩu không hợp lệ hoặc đã hết hạn.'
        )

        return render(
            request,
            'User/reset-password.html'
        )

    if request.method == 'POST':

        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not password:
            messages.error(
                request,
                'Vui lòng nhập mật khẩu mới.'
            )

        elif password != confirm_password:
            messages.error(
                request,
                'Mật khẩu xác nhận không khớp.'
            )

        else:

            user.set_password(password)
            user.save()

            messages.success(
                request,
                'Đổi mật khẩu thành công!'
            )

    return render(
        request,
        'User/reset-password.html'
    )