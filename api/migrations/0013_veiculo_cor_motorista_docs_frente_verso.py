from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_veiculo_foto_veiculo_motorista_foto_livrete'),
    ]

    operations = [
        # Cor do veículo
        migrations.AddField(
            model_name='veiculo',
            name='cor',
            field=models.CharField(blank=True, max_length=50, verbose_name='Cor do veículo'),
        ),
        # BI frente e verso (substituem foto_bi)
        migrations.AddField(
            model_name='motorista',
            name='foto_bi_frente',
            field=models.ImageField(blank=True, null=True, upload_to='documentos/bi/frente/'),
        ),
        migrations.AddField(
            model_name='motorista',
            name='foto_bi_verso',
            field=models.ImageField(blank=True, null=True, upload_to='documentos/bi/verso/'),
        ),
        # Carta frente e verso (substituem foto_carta)
        migrations.AddField(
            model_name='motorista',
            name='foto_carta_frente',
            field=models.ImageField(blank=True, null=True, upload_to='documentos/carta/frente/'),
        ),
        migrations.AddField(
            model_name='motorista',
            name='foto_carta_verso',
            field=models.ImageField(blank=True, null=True, upload_to='documentos/carta/verso/'),
        ),
    ]
