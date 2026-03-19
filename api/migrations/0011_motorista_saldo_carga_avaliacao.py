from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_carga_distancia_km'),
    ]

    operations = [
        migrations.AddField(
            model_name='motorista',
            name='saldo',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                verbose_name='Saldo da carteira (Kz)'
            ),
        ),
        migrations.AddField(
            model_name='carga',
            name='avaliacao',
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                verbose_name='Avaliação do motorista (1-5 estrelas)'
            ),
        ),
    ]
