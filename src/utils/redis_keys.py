class RedisKeys:
    @staticmethod
    def ban(user_id: int | str) -> str:
        return f"ban_status:{user_id}"

    @staticmethod
    def maintenance() -> str:
        return "maintenance_mode"

    @staticmethod
    def user_session(user_id: int | str) -> str:
        return f"user_session:{user_id}"


