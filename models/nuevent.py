# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from datetime import date
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
import re

class ENVEvent(models.Model):
    _name = 'env.event'  # Internal name of a model
    _description = 'Event Information'
    _rec_name = 'event_name'
    
    event_name = fields.Char('Event name', required=True)
    event_location = fields.Char('Event location', required=True)
    event_description = fields.Char('Event description', required=True)
    start_date = fields.Date("Start date of event")
    
    currency_id = fields.Many2one('res.currency', string='Currency')
    
    event_cost = fields.Monetary('Event cost', required=True, currency_field='currency_id')

    parent_id = fields.Many2one('env.event', string='Parent Event')
    child_ids = fields.One2many('env.event', 'parent_id', string='Child Events')
    
    
    event_org = fields.One2many('env.organiser', 'event_id', string='event_org')
    event_team = fields.One2many('env.team', 'team_id', string='event_team')
    sponsor_ids = fields.One2many('env.sponsors', 'event_id', string='Sponsors')
    revenue_id = fields.One2many('env.event.revenue', 'event_id', string="Revenue")

    def name_get(self):
        result = []
        for record in self:
            if(record.parent_id.event_name is False):
                rec_name = "%s" % (record.event_name)
                result.append((record.id, rec_name))
            else:
                rec_name = "%s (%s)" % (record.parent_id.event_name, record.event_name)
                result.append((record.id, rec_name))
        return result

    @api.constrains('start_date')
    def _check_start_date(self):
        for record in self:
            if record.start_date and record.start_date < date.today():
                raise ValidationError('Start date must be greater than or equal to today.')

    @api.constrains('cost')
    def _check_event_cost(self):
        for record in self:
            if record.cost and record.cost < 0:
                raise ValidationError('Event cost cannot be negative.')
    
    
class ENVOrganiser(models.Model):
    _name = 'env.organiser'  # Internal name of a model
    _description = 'Event Organiser'
    
    name = fields.Char(string='Name', required=True)
    email = fields.Char(string='Email', required=True)
    phone_number = fields.Char(string='Phone Number', required=True)
    event_id = fields.Many2one('env.event', string='Event')
    _sql_constraints = [
        ('Org_id', 'UNIQUE(organiser_id)',
         ' Organisation id should be Unique.')]

    @api.constrains('email')
    def _check_email_format(self):
        for record in self:
            if not re.match(r"[^@]+@[^@]+\.[^@]+", record.email):
                raise ValueError('Email address is not in a valid format')


class ENVTeam(models.Model):
    _name = 'env.team'  # Internal name of a model
    _description = 'Event team'
    _rec_name = 'team_name'

    team_name = fields.Char(string='Team Name', required=True)
    team_leader = fields.Char(string='Team Leader', required=True)
    participant_ids = fields.Many2many('env.participant', 'env_teams_participant_rel', 'env_team_id', 'env_participant_id', string='Participants')
    team_id = fields.Many2one('env.event', string='Event')



class ENVParticipant(models.Model):
    _name = 'env.participant'  # Internal name of a model
    _description = 'Event participant'

    name = fields.Char('Name', required=True)
    email = fields.Char('Email', required=True)
    phone = fields.Char('Phone Number', required=True)
    nic = fields.Char('CNIC', required=True)
    team_ids = fields.Many2many('env.team', 'env_teams_participant_rel', 'env_participant_id', 'env_team_id', string='Teams')
    # check

    @api.constrains('nic')
    def _check_nic(self):
        for record in self:
            if record.nic and not re.match(r'^\d{5}-\d{7}-\d$', record.nic):
                raise ValidationError("National ID Card format is not valid.")

    @api.constrains('email')
    def _check_email_format(self):
        for record in self:
            if not re.match(r"[^@]+@[^@]+\.[^@]+", record.email):
                raise ValueError('Email address is not in a valid format')

    @api.model
    def _default_state(self):
        state = self.env['participant.state']
        return state.search([], limit=1)

    stage_id = fields.Many2one('participant.state', default=_default_state)

    _sql_constraints = [
        ('email_unique', 'unique(email)', 'Email must be unique'),
        ('phone_unique', 'unique(phone)', 'Phone number must be unique'),
        ('nic_unique', 'unique(nic)', 'National ID Card must be unique')
    ]

    def write(self, vals):
        result = super(ENVParticipant, self).write(vals)
        if self.stage_id.participant_state == 'paid':
            # Get the participant's team and calculate the total amount paid for all linked events
            total_paid = 0.0
            for team in self.team_ids:
                for event in team.team_id:
                    total_paid += event.event_cost

            # Create the account entry for the participant
            account_vals = {
                'participant_id': self.id,
                'event_id': event.id,
                'type': 'participant',
                'amount_paid': total_paid,
            }
            self.env['env.account'].sudo().create(account_vals)
        elif self.stage_id.participant_state != 'paid':
            self.env['env.account'].sudo().search([('participant_id', '=', self.id)]).unlink()
        return result

class ParticipantStage(models.Model):
    _name = 'participant.state'
    _order = 'sequence,name'

    name = fields.Char()
    sequence = fields.Integer()
    fold = fields.Boolean()
    participant_state = fields.Selection([('pending', 'Pending'), ('paid', 'Paid'), ('cancelled', 'Cancelled')], 'State', default="pending")

class Sponsors(models.Model):
    _name = 'env.sponsors'  # Internal name of a model
    _description = 'Event sponsors'
    _rec_name = 'Sponsor_name'

    Sponsor_name = fields.Char('Name', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency')
    event_id = fields.Many2one('env.event', string='Event')


    sponsor_aid = fields.Monetary('Sponsor Aid', required=True, currency_field='currency_id')


class ENVEventRevenue(models.Model):
    _name = 'env.event.revenue'
    _description = 'Event Revenue'

    event_id = fields.Many2one('env.event', string='Event', required=True, ondelete='cascade')
    total_revenue = fields.Monetary('Total Revenue', compute='_compute_total_revenue', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', related='event_id.currency_id', readonly=True)
    total_sponsor_aid = fields.Monetary('Total Sponsor Aid', compute='_compute_total_sponsor_aid', store=True, currency_field='currency_id')

    @api.depends('event_id')
    def _compute_total_revenue(self):
        for record in self:
            total = 0.0
            for event in record.mapped('event_id'):
                if event.child_ids:
                    for child in event.mapped('child_ids'):
                        for team in child.mapped('event_team'):
                            for participant in team.mapped('participant_ids'):
                                if participant.stage_id.participant_state == 'paid':
                                    total += participant.team_ids.team_id.event_cost

                for team in event.mapped('event_team'):
                    for participant in team.mapped('participant_ids'):
                        if participant.stage_id.participant_state == 'paid':
                            total += participant.team_ids.team_id.event_cost
            record.total_revenue = total

    @api.depends('event_id')
    def _compute_total_sponsor_aid(self):
        for record in self:
            total = 0.0
            if record.event_id.child_ids:
                for child in record.event_id.mapped('child_ids'):
                    for sponsor in child.mapped('sponsor_ids'):
                        total += sponsor.sponsor_aid

            for sponsor in record.event_id.mapped('sponsor_ids'):
                total += sponsor.sponsor_aid
            # record.total_sponsor_aid = sum(record.event_id.mapped('sponsor_ids').sponsor_aid)
            record.total_sponsor_aid = total

# class ENVAccount(models.Model):
#     _name = 'env.account'
#
#     name = fields.Char('Name')
#     type = fields.Selection([('participant', 'Participant Enrollment'), ('sponsor', 'Sponsor'), ('expense', 'Event Expense')], 'Account Type', default="participant")
#     cash_type = fields.Selection([('in', 'Cash Inflow'), ('out', 'Cash Outflow')], 'Cashflow Type', default="in")
#     currency_id = fields.Many2one('res.currency', string='Currency', related='event_id.currency_id', readonly=True)
#     total_sponsor_aid = fields.Monetary('Total Sponsor Aid', store=True, currency_field='currency_id')

class ENVAccount(models.Model):
    _name = 'env.account'
    _description = 'Participant Account'

    participant_id = fields.Many2one('env.participant', string='Participant')
    event_id = fields.Many2one('env.event', string='Event')
    # cash_type = fields.Selection([('in', 'Cash Inflow'), ('out', 'Cash Outflow')], 'Cashflow Type', default="in")
    type = fields.Selection(
        [('participant', 'Participant Enrollment'), ('sponsor', 'Sponsor'), ('expense', 'Event Expense')],
        'Account Type', default="participant")
    amount_paid = fields.Monetary('Amount Paid', currency_field='currency_id')
    description = fields.Text('Description')

    currency_id = fields.Many2one('res.currency', string='Currency', related='event_id.currency_id')

    computed_group = fields.Char(string='Computed Group', compute='_compute_computed_group', store=True)

    @api.depends('event_id', 'type')
    def _compute_computed_group(self):
        for record in self:
            if record.type == 'participant':
                plhd = 'Participants'
            elif record.type == 'sponsor':
                plhd = 'Sponsors'
            elif record.type == 'expense':
                plhd = 'Event Expenses'
            else:
                plhd = ""
            record.computed_group = f"{record.event_id.name_get()[0][1]} - {plhd}"


