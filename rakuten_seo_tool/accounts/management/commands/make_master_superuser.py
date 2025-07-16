from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Make master account a superuser'

    def handle(self, *args, **options):
        try:
            # segishogo@gmail.com をマスターアカウントかつスーパーユーザーにする
            user = User.objects.get(email='segishogo@gmail.com')
            user.is_master = True
            user.is_staff = True
            user.is_superuser = True
            user.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully made {user.email} a master account and superuser'
                )
            )
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    'User segishogo@gmail.com not found'
                )
            )