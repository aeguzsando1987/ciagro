from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("datalayers", "0004_alter_datalayerheader_verbose_names"),
    ]

    operations = [
        migrations.RenameField(
            model_name="datalayerpoints",
            old_name="raw_data",
            new_name="parameters",
        ),
        migrations.RenameIndex(
            model_name="datalayerpoints",
            old_name="idx_dlpoints_raw_data",
            new_name="idx_dlpoints_parameters",
        ),
    ]
