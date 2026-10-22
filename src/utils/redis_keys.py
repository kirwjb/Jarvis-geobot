class RedisKeys:
    @staticmethod
    def ban(user_id: int | str) -> str:
        return f"ban_status:{user_id}"

    @staticmethod
    def maintenance() -> str:
        return "maintenance_mode"

    @staticmethod
    def mute(user_id: int | str) -> str:
        return f"mute_status:{user_id}"

    @staticmethod
    def user_session(user_id: int | str) -> str:
        return f"user_session:{user_id}"

    @staticmethod
    def user_tokens(user_id: int | str) -> str:
        return f"user_tokens:{user_id}"

    @staticmethod
    def rate_limit_bucket(identifier: str) -> str:
        return f"rate_limit:bucket:{identifier}"

    @staticmethod
    def penalty(identifier: str) -> str:
        return f"penalty:{identifier}"

    @staticmethod
    def violations(identifier: str) -> str:
        return f"rate_limit:violations:{identifier}"

