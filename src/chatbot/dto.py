from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
    
    message = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=5000
    )
    session_id = serializers.UUIDField(
        required=False,
        allow_null=True
    )
    
    def validate_message(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Message cannot be empty")
        return value.strip()


class ChatResponseSerializer(serializers.Serializer):
    
    response = serializers.CharField()
    session_id = serializers.UUIDField()
    tools_used = serializers.ListField(child=serializers.CharField())
    tool_calls_count = serializers.IntegerField()
    error = serializers.CharField(required=False, allow_null=True)
