# -*- coding: utf-8 -*-

from openerp.osv import osv
from openerp.osv import fields

from openerp.tools.translate import _

from decimal import Decimal
import datetime


class sc_project (osv.Model):

    def _get_kinds ():
        return [
            ('MEETING', _('Meeting')),
            ('ECM', _('ECM')),
            ('TRAVEL', _('Travel')),
            ('OTHER', _('Other')),
        ]

    def _get_year (self, cr, uid, ids, prop, arg, context):
        res = {}
        for project in self.browse (cr, uid, ids):
            res[project.id] = datetime.datetime.strptime (project.sc_start_date, '%Y-%m-%d').year if project.sc_start_date else None

        return res

    def _get_n_days (self, cr, uid, ids, prop, arg, context):
        res = {}
        for project in self.browse (cr, uid, ids):
            if project.sc_start_date and project.sc_end_date:
                res[project.id] =  (datetime.datetime.strptime (project.sc_end_date, '%Y-%m-%d') \
                                    - datetime.datetime.strptime (project.sc_start_date, '%Y-%m-%d')).days + 1
            else:
                res[project.id] = None

        return res

    def _get_estimate_profit (self, cr, uid, ids, prop, arg, context):
        res = {}
        for project in self.browse (cr, uid, ids):
            revenews = project.sc_estimate_revenews or 0
            costs = project.sc_estimate_costs or 0

            res[project.id] = revenews + costs

        return res

    def _get_estimate_profit_percent (self, cr, uid, ids, prop, arg, context):
        res = {}
        for project in self.browse (cr, uid, ids):
            revenews = project.sc_estimate_revenews or 0
            costs = project.sc_estimate_costs or 0

            if not revenews:
                res[project.id] = 0
            else:
                profit = revenews + costs

                res[project.id] = profit / revenews * 100

        return res

    def update_estimate_profit (self, cr, uid, ids, revenews, costs, context=None):
        revenews = revenews or 0
        costs = costs or 0
        profit = revenews + costs

        if not revenews:
            profit_percent = 0
        else:
            profit_percent = profit / revenews * 100

        return {
            'value': {
                'sc_estimate_profit': profit,
                'sc_estimate_profit_percent': profit_percent,
            },
        }

    def init (self, cr):
        Project = self.pool.get ('project.project')

        for project in Project.browse (cr, 1, Project.search (cr, 1, [])):
            project.write ({}) # force triggering of 'store' functions

    _name = 'project.project'
    _inherit = 'project.project'
    _order = 'sc_start_date'
    _columns = {
        'sc_kind': fields.selection (_get_kinds (), 'Project Kind'),
        'sc_start_date': fields.date ('Event Start Date'),
        'sc_end_date': fields.date ('Event End Date'),
        'free_text_date': fields.char ('Free Text Date'),
        'n_days': fields.function (_get_n_days, string='Days', type='integer', store=True),
        'year': fields.function (_get_year, string='Year', type='integer', store=True),
        'location': fields.char ('Location'),
        'description': fields.text ('Description'),
        'n_expected_pax': fields.integer ('Expected Participants'),
        'n_actual_pax': fields.integer ('Actual Participants'),

        'is_gratis': fields.boolean ('Gratuitous'),
        'has_accommodation': fields.boolean ('Provides Accommodation'),
        'needs_website': fields.boolean ('Needs Website'),
        'has_website': fields.boolean ('Has Website'),
        'website': fields.char ('Website'),

        'sc_estimate_costs': fields.float ('Estimated Costs Amount', track_visibility='onchange'),
        'sc_estimate_revenews': fields.float ('Estimated Revenues Amount', track_visibility='onchange'),
        'sc_estimate_profit': fields.function (_get_estimate_profit, string='Estimated Profit Amount', type='float', store=True),
        'sc_estimate_profit_percent': fields.function (_get_estimate_profit_percent, string='Estimated Profit Percentage', type='float', store=True),
    }
    _defaults = {
        'is_gratis': False,
        'has_accommodation': False,
        'needs_website': False,
        'has_website': False,
    }


class sc_analytic_account (osv.Model):

    def _is_revenew (self, line):
        if not line.journal_id:
            return True if line.amount >= 0 else False

        if line.journal_id.type == 'sale':
            return True

        return False

    def _get_child_cost_revenew (self, cr, uid, ids, prop, arg, context):
        res = {}
        for account in self.browse (cr, uid, ids):
            res[account.id] = {
                'child_cost_revenew_ids': [c.id for c in account.cost_revenew_ids],
                'child_cost_ids': [c.id for c in account.cost_revenew_ids if not self._is_revenew (c)],
                'child_revenew_ids': [c.id for c in account.cost_revenew_ids if self._is_revenew (c)],

                'child_cost_amount': sum ([c.amount for c in account.cost_revenew_ids if not self._is_revenew (c)]),
                'child_revenew_amount': sum ([c.amount for c in account.cost_revenew_ids if self._is_revenew (c)]),
            }

            for child in account.child_ids:
                res[account.id]['child_cost_revenew_ids'].extend ([c.id for c in child.cost_revenew_ids])
                res[account.id]['child_cost_ids'].extend ([c.id for c in child.cost_revenew_ids if not self._is_revenew (c)])
                res[account.id]['child_revenew_ids'].extend ([c.id for c in child.cost_revenew_ids if self._is_revenew (c)])

                res[account.id]['child_cost_amount'] += sum ([c.amount for c in child.cost_revenew_ids if not self._is_revenew (c)])
                res[account.id]['child_revenew_amount'] += sum ([c.amount for c in child.cost_revenew_ids if self._is_revenew (c)])

            res[account.id]['child_profit_amount'] = res[account.id]['child_revenew_amount'] + res[account.id]['child_cost_amount']

            if not res[account.id]['child_revenew_amount']:
                res[account.id]['child_profit_percent'] = 0
            else:
                res[account.id]['child_profit_percent'] = res[account.id]['child_profit_amount'] \
                    * 100 / res[account.id]['child_revenew_amount']

            for attr in ['child_revenew_amount', 'child_cost_amount', 'child_profit_percent', 'child_profit_amount']:
                if res[account.id][attr] is not None:
                    res[account.id][attr] = Decimal.from_float (res[account.id][attr]).quantize (Decimal('.01'))

        return res

    _name = 'account.analytic.account'
    _inherit = 'account.analytic.account'
    _columns = {
        'activity_ids': fields.one2many ('account.analytic.line', 'account_id', 'Activities',
                                         domain=[('move_id', '=', False)]),
        'cost_revenew_ids': fields.one2many ('account.analytic.line', 'account_id', 'Costs and Revenues',
                                     domain=[('move_id', '!=', False)]),
        'child_cost_revenew_ids': fields.function (_get_child_cost_revenew, relation='account.analytic.line',
            multi='child_cost_revenew', string='Costs and Revenues Items', type="one2many", readonly=True),
        'child_cost_ids': fields.function (_get_child_cost_revenew, relation='account.analytic.line',
            multi='child_cost_revenew', string='Costs Items', type="one2many", readonly=True),
        'child_revenew_ids': fields.function (_get_child_cost_revenew, relation='account.analytic.line',
            multi='child_cost_revenew', string='Revenues Items', type="one2many", readonly=True),
        'child_cost_amount': fields.function (_get_child_cost_revenew,
            multi='child_cost_revenew', string='Costs Amount', readonly=True),
        'child_revenew_amount': fields.function (_get_child_cost_revenew,
            multi='child_cost_revenew', string='Revenues Amount', readonly=True),
        'child_profit_amount': fields.function (_get_child_cost_revenew,
            multi='child_profit_revenew', string='Profit Amount', readonly=True),
        'child_profit_percent': fields.function (_get_child_cost_revenew,
            multi='child_profit_revenew', string='Profit Percentage', readonly=True),
    }

    def init (self, cr):
        AnalyticAccount = self.pool.get ('account.analytic.account')

        for account in AnalyticAccount.browse (cr, 1, AnalyticAccount.search (cr, 1, [])):
            account.write ({}) # force triggering of 'store' functions


class sc_analytic_account_line (osv.Model):

    _name = 'account.analytic.line'
    _inherit = 'account.analytic.line'
    _columns = {
        'partner_id': fields.related ('move_id', 'partner_id', type='many2one', relation='res.partner', string="Partner"),
    }


class sc_meeting (osv.Model):

    def _get_scopes ():
        return [
            ('NATIONAL', _('National')),
            ('UE', _('European Union')),
            ('EXTRA_UE', _('Extra European Union')),
        ]

    def _get_fiscal_event_kinds ():
        return [
            ('A', _('Convegno/Seminario/Business Lunch')),
            ('B', _('Congresso')),
            ('C', _('Fiera')),
            ('D', _('Mostra')),
            ('E', _('Festa/Cerimonia')),
        ]

    def _get_fiscal_venue_kinds ():
        return [
            ('1', _('complesso fieristico/centro congressi')),
            ('2', _('villa, dimora storica, casa privata')),
            ('3', _('complesso alberghiero')),
            ('4', _('discoteche')),
            ('5', _('università')),
        ]

    def _get_fiscal_n_pax ():
        return [
            ('<50', '<50'),
            ('51 - 200', '51 - 200'),
            ('201 - 500', '201 - 500'),
            ('501 - 1000', '501 - 1000'),
            ('oltre 1000', 'oltre 1000'),
        ]

    def _get_fiscal_pax_kinds ():
        return [
            ('a', _('persone fisiche')),
            ('b', _('studi legali/notarili')),
            ('c', _('pubblica amministrazione')),
            ('d', _('altri enti pubblici')),
            ('e', _(u'autorità giudiziaria')),
            ('f', _('associazioni ed enti privati (ass. sportive, scientifiche, culturali...)')),
            ('g', _(u'agenzie di pubblicità')),
            ('h', _('case editrici/cinematografiche')),
            ('i', _('imprese, società ed esercenti arti e professioni...')),
            ('l', _('centri di traduzione e interpretariato')),
            ('m', _('società di organizzazione convegni')),
            ('n', _('organismi internazionali')),
            ('o', _('altri')),
            ('p', _('ricavi/compensi conseguiti con clientela estera')),
        ]

    _name = 'project.project'
    _inherit = 'project.project'
    _columns = {
        'venue': fields.char ('Venue'),
        'registration_manager_id': fields.many2one ('hr.employee',
            string='Registration Manager', ondelete='set null', select=True),
        'sponsor_manager_id': fields.many2one ('hr.employee',
            string='Sponsor Manager', ondelete='set null', select=True),
        'scientific_contacts': fields.many2many ('res.partner',
            'sc_contact_project', 'project_id', 'scientific_contact_id', string='Scientific Contacts'),
        'conference_area': fields.char ('Conference Area'),
        'conference_code': fields.char ('Conference Code'),
        'aifa_deadline': fields.date ('AIFA Deadline'),
        'geographical_scope': fields.selection (_get_scopes (), 'Geographical Scope'),
        'fiscal_n_pax': fields.selection (_get_fiscal_n_pax (), 'Fiscal n. Pax'),
        'fiscal_event_kind': fields.selection (_get_fiscal_event_kinds (), 'Fiscal Event Kind'),
        'fiscal_venue_kind': fields.selection (_get_fiscal_venue_kinds (), 'Fiscal Venue Kind'),
        'fiscal_pax_kind': fields.selection (_get_fiscal_pax_kinds (), 'Fiscal Pax Kind'),
    }


class sc_ecm (sc_meeting):

    _name = 'project.project'
    _inherit = 'project.project'
    _columns = {
        'ecm_validation_deadline': fields.date ('Validation Deadline'),
        'ecm_validated': fields.boolean ('Validated'), # FIXME: maybe ==> ecm_validation_date?
        'ecm_report_deadline': fields.date ('Report Deadline'),
        'ecm_report_date': fields.date ('Report Date'),
        'ecm_report_sending_date': fields.date ('Report Sending Date'),
        'ecm_certificate_sending_date': fields.date ('Certificate Sending Date'),
        'ecm_provider_id': fields.many2one ('res.partner', string='Provider', ondelete='set null', select=True),
        'ecm_paid': fields.boolean ('Paid'), # FIXME: maybe ==> ecm_paid_date?
        'ecm_n_credits': fields.float ('Credits'),
        'ecm_categories': fields.text ('Categories'),
    }
    _defaults = {
        'ecm_paid': False,
        'ecm_validated': False,
    }


class sc_travel (osv.Model):

    _name = 'project.project'
    _inherit = 'project.project'
    _columns = {
    }


#class sc_employee (osv.Model):
#
#    _inherit = 'hr.employee'
#    _columns = {
#        'meetings_as_sponsor_manager': fields.one2many ('project.project',
#            'sponsor_manager_id', 'Meetings as sponsor manager'),
#    }

