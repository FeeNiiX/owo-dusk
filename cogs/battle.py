# This file is part of owo-dusk.
#
# Copyright (c) 2024-present EchoQuill
#
# Portions of this file are based on code by EchoQuill, licensed under the
# GNU General Public License v3.0 (GPL-3.0).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import asyncio
import time
import re

from discord.ext import commands, tasks
from utils.notification import notify
#from uwu import MyClient


class Battle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_battle = time.time()
        self.warned = False
        self.cmd = {
            "cmd_name": "",
            "prefix": True,
            "checks": True,
            "id": "battle",
            "slash_cmd_name": "battle",
            "removed": False,
        }

    @property
    def settings(self):
        return self.bot.settings_dict_temp.commands.battle

    @tasks.loop()
    async def battle_watchdog(self):
        await asyncio.sleep(1)

        if self.bot.command_handler_status["captcha"]:
            return

        elapsed = time.time() - self.last_battle

        if elapsed > 65 and not self.warned:
            self.warned = True
            self.bot.command_handler_status["captcha"] = True
            await self.bot.log("Battles Timed Out! Restarting in 20s", "#ffff00")
            notify("Restarting in 20s", "Battles Timed Out!")
            await asyncio.sleep(20)
            self.bot.restart()

    async def cog_load(self):
        if (
            not self.settings.enabled
            or self.bot.settings_dict_temp.cooldowns.reactionBot.huntAndBattle
        ):
            try:
                asyncio.create_task(self.bot.unload_cog("cogs.battle"))
            except Exception:
                pass
        else:
            self.cmd["cmd_name"] = (
                self.bot.alias["battle"]["shortform"]
                if self.settings.shortform
                else self.bot.alias["battle"]["normal"]
            )
            asyncio.create_task(self.bot.put_queue(self.cmd))
            asyncio.create_task(self.battle_watchdog())

    async def cog_unload(self):
        await self.bot.remove_queue(id="battle")

    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            if (
                message.channel.id == self.bot.cm.id
                and message.author.id == self.bot.owo_bot_id
            ):
                if message.embeds:
                    for embed in message.embeds:
                        if (
                            embed.author.name is not None
                            and f"{self.bot.user.display_name} goes into battle!"
                            in embed.author.name
                        ):
                            self.last_battle = time.time()
                            if embed.footer:
                                if self.settings.show_streak:
                                    text = embed.footer.text
                                    foot = re.search(r"You (won|lost)|It's a (tie)", text)
                                    outcome = foot.group(1) or foot.group(2)
                                    nums = re.findall(r"[\d,]+", text)
                                    if not outcome and not nums:
                                        return
                                    custom = f"{outcome} | {' | '.join(nums)}"
                                    await self.bot.log(custom)
                                if "You lost in " in embed.footer.text:
                                    if self.settings.notify_streak_loss:
                                        notify(
                                            embed.footer.text, "You lost your streak!"
                                        )
                            if message.reference is not None:
                                """Return if embed"""
                                referenced_message = (
                                    await message.channel.fetch_message(
                                        message.reference.message_id
                                    )
                                )

                                if (
                                    not referenced_message.embeds
                                    and "You found a **weapon crate**!"
                                    in referenced_message.content
                                ):
                                    # Ignore reply and proceeding!
                                    pass
                                else:
                                    # Return from battle embed reply
                                    return

                            await self.bot.remove_queue(id="battle")
                            await self.bot.sleep(
                                self.settings.get_cd()
                            )
                            self.cmd["cmd_name"] = (
                                self.bot.alias["battle"]["shortform"]
                                if self.settings.shortform
                                else self.bot.alias["battle"]["normal"]
                            )
                            await self.bot.put_queue(self.cmd)
        except Exception as e:
            await self.bot.log(f"Error - {e}, During battle on_message()", "#c25560")


async def setup(bot):
    await bot.add_cog(Battle(bot))
