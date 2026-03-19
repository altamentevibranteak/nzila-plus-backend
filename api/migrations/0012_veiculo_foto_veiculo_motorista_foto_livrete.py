from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_motorista_saldo_carga_avaliacao'),
    ]

    operations = [
        migrations.AddField(
            model_name='veiculo',
            name='foto_veiculo',
            field=models.ImageField(
                blank=True, null=True,
                upload_to='veiculos/fotos/',
                verbose_name='Foto do veículo'
            ),
        ),
        migrations.AddField(
            model_name='motorista',
            name='foto_livrete',
            field=models.ImageField(
                blank=True, null=True,
                upload_to='documentos/livretes/',
                verbose_name='Foto do livrete'
            ),
        ),
        migrations.AddField(
            model_name='motorista',
            name='livrete_verificado',
            field=models.BooleanField(default=False),
        ),
    ]
