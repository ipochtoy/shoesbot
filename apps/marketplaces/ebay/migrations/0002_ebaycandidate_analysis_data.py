from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ebay', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ebaycandidate',
            name='analysis_data',
            field=models.JSONField(blank=True, default=dict, help_text='Latest structured analysis snapshot (brand/model/keywords etc.)'),
        ),
    ]
