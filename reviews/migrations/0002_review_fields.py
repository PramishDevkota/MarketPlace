import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0001_initial'),
        ('orders', '0002_order_amount_paid_order_is_paid_order_payment_type_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='review',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='review',
            name='order',
        ),
        migrations.RemoveField(
            model_name='review',
            name='reviewer',
        ),
        migrations.RemoveField(
            model_name='review',
            name='text',
        ),
        migrations.AddField(
            model_name='review',
            name='comment',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='review',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='orders.order'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='review',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_reviews', to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='review',
            name='rating',
            field=models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1),
                                                               django.core.validators.MaxValueValidator(5)]),
        ),
        migrations.AlterUniqueTogether(
            name='review',
            unique_together={('product', 'user', 'order')},
        ),
    ]
