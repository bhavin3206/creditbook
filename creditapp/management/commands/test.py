from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'This is a test management command.'

    def handle(self, *args, **kwargs):
        from creditapp.models import Customer
        customers = Customer.objects.all()        
        # if customers.exists():
        #     first_customer = customers.first()
        #     first_customer.delete()
        #     self.stdout.write(self.style.SUCCESS(f'Customer {first_customer.name} deleted successfully.'))

        # breakpoint()
        if customers.exists():
            for customer in customers:
                self.stdout.write(self.style.SUCCESS(f'Customer: {customer.name}, Contact: {customer.contact_number}, Email: {customer.email}'))
        else:
            self.stdout.write(self.style.WARNING('No customers found.'))
