"""
Django management command to create a school and school admin account
Usage: python manage.py create_school_admin
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from core.models import School, UserProfile
import getpass


class Command(BaseCommand):
    help = 'Create a new school and school admin account interactively'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('   SCHOOL & ADMIN ACCOUNT SETUP'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

        try:
            # ==================== SCHOOL DETAILS ====================
            self.stdout.write(self.style.WARNING('STEP 1: School Information'))
            self.stdout.write('-' * 60)
            
            school_name = input('School Name: ').strip()
            while not school_name:
                self.stdout.write(self.style.ERROR('School name cannot be empty!'))
                school_name = input('School Name: ').strip()

            # Generate default school code from name
            default_code = ''.join(c.upper() for c in school_name if c.isalnum())[:6]
            school_code = input(f'School Code (default: {default_code}): ').strip() or default_code
            
            # Check if school code already exists
            while School.objects.filter(code=school_code).exists():
                self.stdout.write(self.style.ERROR(f'School code "{school_code}" already exists!'))
                school_code = input('Please enter a different school code: ').strip()

            school_address = input('School Address (optional): ').strip()
            school_phone = input('School Phone (optional): ').strip()
            school_email = input('School Email (optional): ').strip()

            # ==================== ADMIN ACCOUNT DETAILS ====================
            self.stdout.write('\n')
            self.stdout.write(self.style.WARNING('STEP 2: School Admin Account'))
            self.stdout.write('-' * 60)
            
            admin_username = input('Admin Username: ').strip()
            while not admin_username:
                self.stdout.write(self.style.ERROR('Username cannot be empty!'))
                admin_username = input('Admin Username: ').strip()
            
            # Check if username already exists
            while User.objects.filter(username=admin_username).exists():
                self.stdout.write(self.style.ERROR(f'Username "{admin_username}" already exists!'))
                admin_username = input('Please enter a different username: ').strip()

            admin_email = input('Admin Email: ').strip()
            admin_first_name = input('First Name: ').strip()
            admin_last_name = input('Last Name: ').strip()
            
            # Password with confirmation
            while True:
                admin_password = getpass.getpass('Password: ')
                if not admin_password:
                    self.stdout.write(self.style.ERROR('Password cannot be empty!'))
                    continue
                    
                admin_password_confirm = getpass.getpass('Confirm Password: ')
                
                if admin_password != admin_password_confirm:
                    self.stdout.write(self.style.ERROR('Passwords do not match! Try again.'))
                    continue
                    
                if len(admin_password) < 8:
                    self.stdout.write(self.style.ERROR('Password must be at least 8 characters!'))
                    continue
                    
                break

            # ==================== CONFIRMATION ====================
            self.stdout.write('\n')
            self.stdout.write(self.style.WARNING('STEP 3: Confirm Details'))
            self.stdout.write('-' * 60)
            self.stdout.write(f'School Name:     {school_name}')
            self.stdout.write(f'School Code:     {school_code}')
            self.stdout.write(f'School Address:  {school_address or "(not provided)"}')
            self.stdout.write(f'School Phone:    {school_phone or "(not provided)"}')
            self.stdout.write(f'School Email:    {school_email or "(not provided)"}')
            self.stdout.write('')
            self.stdout.write(f'Admin Username:  {admin_username}')
            self.stdout.write(f'Admin Email:     {admin_email or "(not provided)"}')
            self.stdout.write(f'Admin Name:      {admin_first_name} {admin_last_name}')
            self.stdout.write('-' * 60)
            
            confirm = input('\nCreate school and admin account? (yes/no): ').strip().lower()
            
            if confirm not in ['yes', 'y']:
                self.stdout.write(self.style.WARNING('\n❌ Setup cancelled.'))
                return

            # ==================== CREATE SCHOOL & ADMIN ====================
            self.stdout.write('\n')
            self.stdout.write(self.style.WARNING('Creating school and admin account...'))
            
            with transaction.atomic():
                # Create School
                school = School.objects.create(
                    name=school_name,
                    code=school_code,
                    address=school_address,
                    phone=school_phone,
                    email=school_email
                )
                self.stdout.write(self.style.SUCCESS(f'✓ School "{school.name}" created'))

                # Create Admin User
                admin_user = User.objects.create_user(
                    username=admin_username,
                    email=admin_email,
                    password=admin_password,
                    first_name=admin_first_name,
                    last_name=admin_last_name,
                    is_staff=True  # Allow access to teacher portal
                )
                self.stdout.write(self.style.SUCCESS(f'✓ User account "{admin_user.username}" created'))

                # Create UserProfile
                user_profile = UserProfile.objects.create(
                    user=admin_user,
                    role='school_admin',
                    school=school
                )
                self.stdout.write(self.style.SUCCESS(f'✓ User profile created with school_admin role'))

            # ==================== SUCCESS ====================
            self.stdout.write('\n')
            self.stdout.write(self.style.SUCCESS('='*60))
            self.stdout.write(self.style.SUCCESS('   ✅ SETUP COMPLETE!'))
            self.stdout.write(self.style.SUCCESS('='*60))
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f'School:   {school.name} ({school.code})'))
            self.stdout.write(self.style.SUCCESS(f'Admin:    {admin_user.username}'))
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('Next steps:'))
            self.stdout.write('  1. Login at: http://127.0.0.1:8000/accounts/login/')
            self.stdout.write(f'     Username: {admin_username}')
            self.stdout.write(f'     Password: (the one you entered)')
            self.stdout.write('  2. Start creating teachers and students!')
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

        except KeyboardInterrupt:
            self.stdout.write(self.style.ERROR('\n\n❌ Setup cancelled by user.'))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n\n❌ Error: {str(e)}'))
            self.stdout.write(self.style.ERROR('Setup failed. Please try again.'))
            return