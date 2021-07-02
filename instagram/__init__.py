from .main import Instagram


def setup(bot):
    bot.add_cog(Instagram(bot))
