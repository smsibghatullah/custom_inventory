# MIR Chatter Mention Notify

## Purpose

Odoo 17 module.

When any internal user is mentioned/tagged in chatter on any model, the mentioned user receives:

1. Private Discuss chat message
2. Email notification

## How it works

The module inherits `mail.message` globally. When a chatter message is created, it extracts mentioned partners from the HTML body and `partner_ids`.

If the mentioned partner belongs to an active internal user, the module:

- Finds or creates a private `discuss.channel` chat between the author and the mentioned partner.
- Posts a message in Discuss.
- Sends an email using `mail.mail`.

## Important

This module does not require custom code per model.

Any model with chatter/mail.thread will work.

## Configuration

Settings > General Settings > MIR Chatter Mention Notify

Options:

- Send Discuss message on chatter mention
- Send email on chatter mention

Both are enabled by default.

## Install

Copy the module folder to addons path and update:

```bash
./odoo-bin -d YOUR_DB -u mir_chatter_mention_notify
```

## Usage

Open any chatter-enabled record and type a message mentioning a user with @.

Example:

`@Ali please check this record.`

Ali will receive a Discuss message and email.
