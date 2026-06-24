# Generated for smart assembly dashboard Django/MySQL integration
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name="Order", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("command", models.CharField(max_length=255)), ("destination", models.CharField(default="A", max_length=16)), ("parts", models.JSONField(default=list)), ("status", models.CharField(default="ORDER_RECEIVED", max_length=64)), ("created_at", models.DateTimeField(auto_now_add=True))]),
        migrations.CreateModel(name="FactoryEvent", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("event_type", models.CharField(max_length=96)), ("state", models.CharField(blank=True, max_length=96)), ("payload", models.JSONField(default=dict)), ("created_at", models.DateTimeField(auto_now_add=True))]),
        migrations.CreateModel(name="VisionDetection", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("label", models.CharField(max_length=80)), ("confidence", models.FloatField(blank=True, null=True)), ("bbox", models.JSONField(default=dict)), ("camera_point_mm", models.JSONField(default=list)), ("created_at", models.DateTimeField(auto_now_add=True))]),
        migrations.CreateModel(name="DeliveryResult", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("destination", models.CharField(max_length=16)), ("target_pose", models.JSONField(default=dict)), ("success", models.BooleanField(default=False)), ("raw_result", models.JSONField(default=dict)), ("created_at", models.DateTimeField(auto_now_add=True))]),
        migrations.CreateModel(name="EmergencyStopLog", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("source", models.CharField(default="dashboard", max_length=80)), ("reason", models.CharField(blank=True, max_length=255)), ("payload", models.JSONField(default=dict)), ("created_at", models.DateTimeField(auto_now_add=True))]),
    ]
