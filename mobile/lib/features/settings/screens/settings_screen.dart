import 'package:flutter/material.dart';
import '../../../core/api/api_client.dart';
import '../../../core/config/server_config.dart';

/// Lets the user point the app at a different backend server address.
/// Reachable even when logged out, since a stale address (e.g. after the
/// Tailscale IP changes) can prevent login from ever succeeding.
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _hostCtrl;

  @override
  void initState() {
    super.initState();
    _hostCtrl = TextEditingController(text: ServerConfig.host);
  }

  @override
  void dispose() {
    _hostCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    await ServerConfig.setHost(_hostCtrl.text);
    ApiClient().updateBaseUrl();
    setState(() => _hostCtrl.text = ServerConfig.host);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Server address updated')),
    );
  }

  Future<void> _reset() async {
    await ServerConfig.resetToDefault();
    ApiClient().updateBaseUrl();
    setState(() => _hostCtrl.text = ServerConfig.host);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Server address reset to default')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Backend server address',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 4),
              const Text(
                'If the server IP changes (e.g. Tailscale), update it here. '
                'Example: 100.101.102.103:8010',
                style: TextStyle(color: Colors.grey),
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _hostCtrl,
                keyboardType: TextInputType.url,
                autocorrect: false,
                decoration: const InputDecoration(
                  labelText: 'Server address',
                  hintText: 'e.g. 100.101.102.103:8010',
                  prefixIcon: Icon(Icons.dns_outlined),
                  border: OutlineInputBorder(),
                ),
                validator: (v) => v == null || v.trim().isEmpty
                    ? 'Enter a server address'
                    : null,
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _save,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  backgroundColor: Colors.deepOrange,
                  foregroundColor: Colors.white,
                ),
                child: const Text('Save'),
              ),
              const SizedBox(height: 8),
              OutlinedButton(
                onPressed: _reset,
                child: Text('Reset to default (${ServerConfig.defaultHost})'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
