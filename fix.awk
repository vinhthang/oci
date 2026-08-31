BEGIN { in_vol = 0; in_mount = 0 }
{
    if (NR == 562) {
        print "            - name: grafana-alerting"
        print "              mountPath: /etc/grafana/provisioning/alerting/alerting.yaml"
        print "              subPath: alerting.yaml"
        print "            - name: grafana-alert-rules"
        print "              mountPath: /etc/grafana/provisioning/alerting/rules.yaml"
        print "              subPath: rules.yaml"
        next
    }
    if (NR == 563) {
        next
    }
    if (NR == 579) {
        print "        - name: grafana-alerting"
        print "          configMap:"
        print "            name: grafana-alerting"
        print "        - name: grafana-alert-rules"
        print "          configMap:"
        print "            name: grafana-alert-rules"
        next
    }
    if (NR == 580 || NR == 581) {
        next
    }
    print $0
}
