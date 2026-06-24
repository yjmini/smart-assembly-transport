from django.db import models


class Order(models.Model):
    command = models.CharField(max_length=255)
    destination = models.CharField(max_length=16, default="A")
    parts = models.JSONField(default=list)
    status = models.CharField(max_length=64, default="ORDER_RECEIVED")
    created_at = models.DateTimeField(auto_now_add=True)


class FactoryEvent(models.Model):
    event_type = models.CharField(max_length=96)
    state = models.CharField(max_length=96, blank=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class VisionDetection(models.Model):
    label = models.CharField(max_length=80)
    confidence = models.FloatField(null=True, blank=True)
    bbox = models.JSONField(default=dict)
    camera_point_mm = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)


class DeliveryResult(models.Model):
    destination = models.CharField(max_length=16)
    target_pose = models.JSONField(default=dict)
    success = models.BooleanField(default=False)
    raw_result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class EmergencyStopLog(models.Model):
    source = models.CharField(max_length=80, default="dashboard")
    reason = models.CharField(max_length=255, blank=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
