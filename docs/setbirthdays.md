# 🎂 Set Birthdays Command

The `/setbirthdays` command allows administrators to set birthdays for members in the server.

## 📋 Usage

```
/setbirthdays [user]
```

## 🔧 Parameters

• **user**: The member to set a birthday for (required)

## 🛡️ Permissions

This command requires **Administrator** permissions to use.

## 📝 Description

When used, this command will:

1. Open a modal input form prompting for the birthday date
2. Allow entering the date in MM-DD format (e.g., `12-25` for December 25th)
3. Save the birthday information to the server's birthday database
4. Display a confirmation message showing the set birthday

## 🖼️ Example

![setbirthdays example](images/setbirthdays-example.png)

## 💡 Notes

• The bot automatically handles birthdays and will send announcements on the day
• Multiple date formats are supported: MM-DD, MM/DD, and MM.DD
• Dates are validated to ensure they're in a proper calendar format
• After setting a birthday, the bot will calculate and display when the next occurrence will be

## 🔄 Related Commands

• `/birthdays`: Main birthday command for members to set their own birthdays
• Birthdays can also be set through the Birthday Menu by clicking on "Set My Birthday"

## 🎁 Birthday Announcements

Birthday announcements are posted automatically at midnight in the following channels (in order of preference):
1. A channel named "birthdays" or "birthday"
2. A channel named "general" or "chat"
3. The first channel the bot can post in

Announcements include:
• A celebratory embed with the birthday member's mention
• Custom birthday messages for the member
• Footer text reminding others how to add their own birthdays 