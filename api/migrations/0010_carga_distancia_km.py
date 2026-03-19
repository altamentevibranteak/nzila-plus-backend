from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_cliente_foto_perfil_motorista_foto_perfil'),
    ]

    operations = [
        migrations.AddField(
            model_name='carga',
            name='distancia_km',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                verbose_name='Distância em km (calculada pelo frontend)'
            ),
        ),
    ]