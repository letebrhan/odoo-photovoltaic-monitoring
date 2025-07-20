from odoo import models, fields, api, _, exceptions
from logging import getLogger
import json
_logger = getLogger(__name__)

class PlantsPhotovoltaic(models.Model):
    """PlantsPhotovoltaic class definition."""
    _inherit = 'plants'

    def create_daily_dashboard_charts(self, dashboard):
        """create_daily_dashboard_charts method."""
        self.ensure_one()
        DashboardWidget = self.env['eko.dynamic.dashboard.widget']
        EkogridChart = self.env['ekogrid.chart']
        gridstack_conf = dict()
        base_domain_chart = [('plant_id', '=', self.id), ('chart_class', '=', 'dashboard')]
        base_chart_attributes = dict(plant_ids=[(6, 0, [self.id])], chart_class='dashboard', show_legend=False, show_navigator=False, show_legend_button=True)
        base_domain_dashboard = [('dashboard_id', '=', dashboard.id)]
        base_dashboard_attribute = dict(type='ekogrid.chart', dashboard_id=dashboard.id)
        ' # create PV Perofrmance '
        pv_dashboardWidget_id = DashboardWidget.search(base_domain_dashboard + [('name', '=', 'PV Performance - Daily'), ('type', '=', 'performance_graph')])
        if not pv_dashboardWidget_id:
            pv_dashboardWidget_id = DashboardWidget.create(dict(name='PV Performance - Daily', pv_plant_id=self.id, type='performance_graph', dashboard_id=dashboard.id))
        gridstack_conf.update({pv_dashboardWidget_id.id: {'y': 0, 'x': 0, 'height': 4, 'width': 6}})
        ' # create Generated AC Energy dashboard'
        pv_meter = self.get_tasks('PV Production', 'AC Energy Partial')
        if pv_meter:
            subtitle = 'PV Production'
            domain_pv_meter = base_domain_chart + [('title', '=', 'Generated AC Energy'), ('subtitle', '=', 'PV Production'), ('task_ids', 'in', pv_meter.ids)]
            base_chart_attributes.update(dict(title='Generated AC Energy', subtitle=subtitle, type='highstock', time_frame='today', aggregate='hour', stacking_type='normal'))
            chart_id_pv_meter = EkogridChart.search(domain_pv_meter)
            if not chart_id_pv_meter:
                chart_id_pv_meter = EkogridChart.create(base_chart_attributes)
                [chart_id_pv_meter.add_serie_with_tasks_default([task.id]) for task in pv_meter]
            dashboardWidget_id = DashboardWidget.search(base_domain_dashboard + [('chart_id', '=', chart_id_pv_meter.id)])
            if not dashboardWidget_id:
                base_dashboard_attribute.update(dict(name=chart_id_pv_meter.title + ' Daily', chart_id=chart_id_pv_meter.id))
                dashboardWidget_id = DashboardWidget.create(base_dashboard_attribute)
            gridstack_conf.update({dashboardWidget_id.id: {'y': 0, 'x': 6, 'height': 4, 'width': 6}})
        ' # create AC Power Dashboard'
        inv_power = self.get_tasks('Inverter', 'AC Power')
        sensor_irr = self.get_tasks('Sensor', 'Irradiance')
        if inv_power or sensor_irr:
            base_chart_attributes.update(dict(title='AC Power', type='highstock', subtitle='Inverter', time_frame='today', aggregate='10 minute', stacking_type=False))
            chart_ids = EkogridChart.default_graphs_divider(inv_power, base_domain_chart, base_chart_attributes)
            if chart_ids:
                if sensor_irr:
                    [chart_id.add_serie_with_tasks_default(sensor_irr.ids) for chart_id in chart_ids]
                for chart_id in chart_ids:
                    dashboardWidget_id = DashboardWidget.search([('chart_id', '=', chart_id.id), ('dashboard_id', '=', dashboard.id)])
                    if not dashboardWidget_id:
                        base_dashboard_attribute.update(dict(name=chart_id.title + ' Daily', chart_id=chart_id.id))
                        dashboardWidget_id = DashboardWidget.create(base_dashboard_attribute)
                    gridstack_conf.update({dashboardWidget_id.id: {'y': 4, 'x': 0, 'height': 4, 'width': 12}})
            elif sensor_irr:
                chart_id_ac_power = EkogridChart.create(base_chart_attributes)
                chart_id_ac_power.add_serie_with_tasks_default(sensor_irr.ids)
                dashboardWidget_id = DashboardWidget.search([('chart_id', '=', chart_id_ac_power.id), ('dashboard_id', '=', dashboard.id)])
                if not dashboardWidget_id:
                    base_dashboard_attribute.update(dict(name=chart_id_ac_power.title + ' Daily', chart_id=chart_id_ac_power.id))
                    dashboardWidget_id = DashboardWidget.create(base_dashboard_attribute)
                gridstack_conf.update({dashboardWidget_id.id: {'y': 4, 'x': 0, 'height': 4, 'width': 12}})
        ' create DC Current Dashboard'
        inv_dc_curr = self.get_tasks('Inverter', 'DC Current')
        if inv_dc_curr:
            base_chart_attributes.update(dict(title='DC Current', subtitle='Inverter', time_frame='today', aggregate='10 minute', stacking_type=False))
            chart_ids = EkogridChart.default_graphs_divider(inv_dc_curr, base_domain_chart, base_chart_attributes)
            for chart_id in chart_ids:
                dashboardWidget_id = DashboardWidget.search([('chart_id', '=', chart_id.id), ('dashboard_id', '=', dashboard.id)])
                if not dashboardWidget_id:
                    base_dashboard_attribute.update(dict(name=chart_id.title + ' Daily', chart_id=chart_id.id))
                    dashboardWidget_id = DashboardWidget.create(base_dashboard_attribute)
                gridstack_conf.update({dashboardWidget_id.id: {'y': 8, 'x': 0, 'height': 4, 'width': 4}})
        '  create AC Voltage – Inverter Dashboard'
        inv_ac_vol = self.get_tasks('Inverter', 'AC Voltage')
        if inv_ac_vol:
            base_chart_attributes.update(dict(title='AC Voltage -', subtitle='Inverter', time_frame='today', aggregate='10 minute', stacking_type=False))
            chart_ids = EkogridChart.default_graphs_divider(inv_ac_vol, base_domain_chart, base_chart_attributes)
            for chart_id in chart_ids:
                dashboardWidget_id = DashboardWidget.search([('chart_id', '=', chart_id.id), ('dashboard_id', '=', dashboard.id)])
                if not dashboardWidget_id:
                    base_dashboard_attribute.update(dict(name=chart_id.title + ' Daily', chart_id=chart_id.id))
                    dashboardWidget_id = DashboardWidget.create(base_dashboard_attribute)
                gridstack_conf.update({dashboardWidget_id.id: {'y': 8, 'x': 4, 'height': 4, 'width': 4}})
        ' Create Irradiance vs AC Energy Dashboard'
        if sensor_irr or pv_meter:
            domain_sensor_irr = base_domain_chart + [('title', '=', 'Irradiance vs AC Energy'), ('subtitle', '=', 'Sensor'), ('task_ids', 'in', (sensor_irr + pv_meter).ids)]
            base_chart_attributes.update(dict(title='Irradiance vs AC Energy', subtitle='Sensor', type='highstock', time_frame='today', aggregate='10 minute', stacking_type=False))
            chart_id_sensor_irr = EkogridChart.search(domain_sensor_irr)
            if not chart_id_sensor_irr:
                chart_id_sensor_irr = EkogridChart.create(base_chart_attributes)
                [chart_id_sensor_irr.add_serie_with_tasks_default([task.id], color='#8b0000') for task in sensor_irr]
                chart_id_sensor_irr.add_serie_with_tasks_default(task_ids=pv_meter.ids, color='#FF7F00', name='Total AC Energy', function='sum', function_many='sum')
            dashboardWidget_id = DashboardWidget.search(base_domain_dashboard + [('chart_id', '=', chart_id_sensor_irr.id)])
            if not dashboardWidget_id:
                base_dashboard_attribute.update(dict(name=chart_id_sensor_irr.title, chart_id=chart_id_sensor_irr.id))
                dashboardWidget_id = DashboardWidget.create(base_dashboard_attribute)
            gridstack_conf.update({dashboardWidget_id.id: {'y': 8, 'x': 8, 'height': 4, 'width': 4}})
        dashboard.grid_stack_config = json.dumps(gridstack_conf)

    def create_weekly_monthly_dashboard_charts(self, dashboard):
        """create_weekly_monthly_dashboard_charts method."""
        self.ensure_one()
        DashboardWidget = self.env['eko.dynamic.dashboard.widget']
        EkogridChart = self.env['ekogrid.chart']
        gridstack_conf = dict()
        base_domain_chart = [('plant_id', '=', self.id), ('chart_class', '=', 'dashboard')]
        base_chart_attributes = dict(plant_ids=[(6, 0, [self.id])], chart_class='dashboard', show_navigator=False, show_legend_button=True)
        base_domain_dashboard = [('dashboard_id', '=', dashboard.id)]
        base_dashboard_attribute = dict(type='ekogrid.chart', dashboard_id=dashboard.id)
        ' # create PV Perofrmance '
        pv_dashboardWidget_id = DashboardWidget.search(base_domain_dashboard + [('name', '=', 'PV Performance - Weekly & Monthly'), ('type', '=', 'performance_graph')])
        if not pv_dashboardWidget_id:
            pv_dashboardWidget_id = DashboardWidget.create(dict(name='PV Performance - Weekly & Monthly', pv_plant_id=self.id, type='performance_graph', pg_aggregate='month', pg_time_frame='last_year', dashboard_id=dashboard.id))
        gridstack_conf.update({pv_dashboardWidget_id.id: {'y': 0, 'x': 4, 'height': 6, 'width': 8}})
        ' Create AC Power – Plant'
        pv_ac_pow = self.get_tasks('PV Production', 'AC Power')
        if pv_ac_pow:
            domain_pv_ac_pow = base_domain_chart + [('title', '=', 'AC Power – Plant'), ('subtitle', '=', 'PV Production'), ('task_ids', 'in', pv_ac_pow.ids)]
            base_chart_attributes.update(dict(title='AC Power – Plant', subtitle='PV Production', type='solidgauge', time_frame='7', aggregate='10 minute', stacking_type=False, start_radius=50, show_legend=True))
            chart_id_pv_ac_pow = EkogridChart.search(domain_pv_ac_pow)
            if not chart_id_pv_ac_pow:
                chart_id_pv_ac_pow = EkogridChart.create(base_chart_attributes)
                name = len(pv_ac_pow) == 1 and pv_ac_pow.name or 'Total AC Power'
                chart_id_pv_ac_pow.add_serie_with_tasks_default(task_ids=pv_ac_pow.ids, color='#0000FF', name=name, max=self.power * 1000, function='sum')
            dashboardWidget_id_pv_ac_pow = DashboardWidget.search(base_domain_dashboard + [('chart_id', '=', chart_id_pv_ac_pow.id)])
            if not dashboardWidget_id_pv_ac_pow:
                base_dashboard_attribute.update(dict(name=chart_id_pv_ac_pow.title + '- Weekly & Monthly', chart_id=chart_id_pv_ac_pow.id))
                dashboardWidget_id_pv_ac_pow = DashboardWidget.create(base_dashboard_attribute)
            gridstack_conf.update({dashboardWidget_id_pv_ac_pow.id: {'y': 0, 'x': 0, 'height': 3, 'width': 4}})
        ' Create AC PR – Plant'
        inv_pv_pr = self.get_tasks('PV Production', 'AC PR')
        if inv_pv_pr:
            domain_inv_pv_pr = base_domain_chart + [('title', '=', 'AC PR – Plant'), ('subtitle', '=', 'PV Production'), ('task_ids', 'in', inv_pv_pr.ids)]
            base_chart_attributes.update(dict(title='AC PR – Plant', subtitle='PV Production', type='solidgauge', time_frame='7', aggregate='week', stacking_type=False, start_radius=50, show_legend=True))
            chart_id_inv_pv_pr = EkogridChart.search(domain_inv_pv_pr)
            if not chart_id_inv_pv_pr:
                chart_id_inv_pv_pr = EkogridChart.create(base_chart_attributes)
                name = len(inv_pv_pr) == 1 and inv_pv_pr.name or 'Total AC PR'
                chart_id_inv_pv_pr.add_serie_with_tasks_default(task_ids=inv_pv_pr.ids, color='#008000', name=name, max=1)
            dashboardWidget_id_pv_pr = DashboardWidget.search(base_domain_dashboard + [('chart_id', '=', chart_id_inv_pv_pr.id)])
            if not dashboardWidget_id_pv_pr:
                base_dashboard_attribute.update(dict(name=chart_id_inv_pv_pr.title + '- Weekly & Monthly', chart_id=chart_id_inv_pv_pr.id))
                dashboardWidget_id_pv_pr = DashboardWidget.create(base_dashboard_attribute)
            gridstack_conf.update({dashboardWidget_id_pv_pr.id: {'y': 3, 'x': 0, 'height': 3, 'width': 4}})
        ' Create Generated AC Energy - Inverter'
        inv_pv_meter = self.get_tasks('Inverter', 'AC Energy Partial')
        if inv_pv_meter:
            domain_inv_pv_meter = base_domain_chart + [('title', '=', 'Generated AC Energy - Inverter'), ('subtitle', '=', 'Inverter'), ('task_ids', 'in', inv_pv_meter.ids)]
            base_chart_attributes.update(dict(title='Generated AC Energy - Inverter', subtitle='Inverter', type='highstock', time_frame='31', aggregate='day', stacking_type='normal', start_radius=0, show_legend=False))
            chart_id_inv_pv_meter = EkogridChart.search(domain_inv_pv_meter)
            if not chart_id_inv_pv_meter:
                chart_id_inv_pv_meter = EkogridChart.create(base_chart_attributes)
                [chart_id_inv_pv_meter.add_serie_with_tasks_default([task.id]) for task in inv_pv_meter]
            dashboardWidget_id_pv_meter = DashboardWidget.search(base_domain_dashboard + [('chart_id', '=', chart_id_inv_pv_meter.id)])
            if not dashboardWidget_id_pv_meter:
                base_dashboard_attribute.update(dict(name=chart_id_inv_pv_meter.title + '- Weekly & Monthly', chart_id=chart_id_inv_pv_meter.id))
                dashboardWidget_id_pv_meter = DashboardWidget.create(base_dashboard_attribute)
            gridstack_conf.update({dashboardWidget_id_pv_meter.id: {'y': 6, 'x': 0, 'height': 4, 'width': 8}})
        ' Create AC PR – Inverter'
        inv_ac_pr = self.get_tasks('Inverter', 'AC PR')
        if inv_ac_pr:
            domain_inv_ac_pr = base_domain_chart + [('title', '=', 'AC PR – Inverter'), ('subtitle', '=', 'Inverter'), ('task_ids', 'in', inv_ac_pr.ids)]
            base_chart_attributes.update(dict(title='AC PR – Inverter', subtitle='Inverter', type='highstock', time_frame='today', aggregate='day', stacking_type=False, start_radius=0, show_legend=False))
            chart_id_inv_ac_pr = EkogridChart.search(domain_inv_ac_pr)
            if not chart_id_inv_ac_pr:
                chart_id_inv_ac_pr = EkogridChart.create(base_chart_attributes)
                [chart_id_inv_ac_pr.add_serie_with_tasks_default([task.id]) for task in inv_ac_pr]
            dashboardWidget_id_ac_pr = DashboardWidget.search([('chart_id', '=', chart_id_inv_ac_pr.id), ('dashboard_id', '=', dashboard.id)])
            if not dashboardWidget_id_ac_pr:
                base_dashboard_attribute.update(dict(name=chart_id_inv_ac_pr.title + '- Weekly & Monthly', chart_id=chart_id_inv_ac_pr.id))
                dashboardWidget_id_ac_pr = DashboardWidget.create(base_dashboard_attribute)
            gridstack_conf.update({dashboardWidget_id_ac_pr.id: {'y': 6, 'x': 8, 'height': 4, 'width': 4}})
        dashboard.grid_stack_config = json.dumps(gridstack_conf)

    def adjust_width_height_dashboardgrid(self, charts_DWidget_ids):
        """adjust_width_height_dashboardgrid method."""
        gridstack_conf = dict()
        if len(charts_DWidget_ids) > 0:
            charts_DWidget_ids = [charts_DWidget_ids[i:i + 2] for i in range(0, len(charts_DWidget_ids), 2)]
            x = y = 0
            for i in range(len(charts_DWidget_ids)):
                for j in range(len(charts_DWidget_ids[i])):
                    gridstack_conf.update({charts_DWidget_ids[i][j]: {'y': y + i * 4, 'x': (x + 6) * 2 * j - j * 6, 'height': 4, 'width': 6}})
        return gridstack_conf

    def create_default_dashboard_parent_fn(self):
        """create_default_dashboard_parent_fn method."""
        self.ensure_one()
        Dashboard = self.env['eko.dynamic.dashboard']
        dashboard_name = 'Dashboard 1'
        sub_title = 'Daily values'
        dashboard = Dashboard.search([('name', '=', dashboard_name), ('plant_id', '=', self.id), ('sub_title', '=', sub_title)])
        if dashboard and len(dashboard) > 1:
            raise exceptions.ValidationError('Warning! More than one Daily values Dashboard charts are available.')
        if not dashboard:
            dashboard = Dashboard.create(dict(name=dashboard_name, sub_title=sub_title, plant_ids=[(6, 0, [self.id])]))
        self.dynamic_dashboard_default_id = dashboard
        self.create_daily_dashboard_charts(dashboard)
        self.create_default_dashboards_child_fn(dashboard)

    def create_default_dashboards_child_fn(self, dashboard_id_parent):
        """create_default_dashboards_child_fn method."""
        self.ensure_one()
        Dashboard = self.env['eko.dynamic.dashboard']
        sub_title = 'Weekly and Monthly values'
        dashboard_name = 'Dashboard 2'
        dashboard = Dashboard.search([('name', '=', dashboard_name), ('plant_id', '=', self.id), ('sub_title', '=', sub_title)])
        if dashboard and len(dashboard) > 1:
            raise exceptions.ValidationError('Warning! More than one Weekly/Monthly values Dashboard charts are available.')
        if not dashboard:
            dashboard = Dashboard.create(dict(name=dashboard_name, sub_title=sub_title, plant_ids=[(6, 0, [self.id])], parent_id=dashboard_id_parent.id))
        self.create_weekly_monthly_dashboard_charts(dashboard)