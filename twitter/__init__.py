from .twitter import Twitter

___red_end_user_data_statement__ = (
    "This cog does not persistently store data about users."
)


def setup(bot):
    bot.add_cog(Twitter(bot))